import numpy as np
from scipy.signal import firls, freqz


FS_INPUT = 10_000_000
R = 8
N = 3
M = 1

FS_OUTPUT = FS_INPUT / R

TAPS = 31
PASSBAND_EDGE = 200_000
STOPBAND_START = 350_000
STOPBAND_TARGET_DB = -40.0
PASSBAND_LIMIT_DB = 0.25

COEFFICIENT_WIDTH = 18
FRACTIONAL_BITS = 17
COEFFICIENT_SCALE = 1 << FRACTIONAL_BITS

PASSBAND_SEGMENTS = 8
PASSBAND_WEIGHT = 100.0
STOPBAND_WEIGHT = 1.0
RESPONSE_POINTS = 65_536


def cic_magnitude(
	frequency_hz: float | np.ndarray,
) -> float | np.ndarray:
	"""Return the unnormalized magnitude of the frozen CIC decimator."""
	frequencies = np.asarray(frequency_hz, dtype=float)

	if np.any(frequencies < 0):
		raise ValueError("frequency_hz must not be negative")

	magnitude = np.empty_like(frequencies)
	zero_frequency = frequencies == 0

	magnitude[zero_frequency] = (R * M) ** N

	nonzero_frequency = ~zero_frequency

	if np.any(nonzero_frequency):
		numerator = np.sin(
			np.pi
			* frequencies[nonzero_frequency]
			* R
			* M
			/ FS_INPUT
		)

		denominator = np.sin(
			np.pi
			* frequencies[nonzero_frequency]
			/ FS_INPUT
		)

		magnitude[nonzero_frequency] = np.abs(
			numerator / denominator
		) ** N

	if np.isscalar(frequency_hz):
		return float(magnitude)

	return magnitude


def build_firls_specification(
) -> tuple[list[float], list[float], list[float]]:
	"""Build the passband-compensation and stopband design targets."""
	passband_edges = np.linspace(
		0,
		PASSBAND_EDGE,
		PASSBAND_SEGMENTS + 1,
	)

	bands: list[float] = []
	desired: list[float] = []
	weights: list[float] = []

	for lower_edge, upper_edge in zip(
		passband_edges[:-1],
		passband_edges[1:],
	):
		bands.extend([
			float(lower_edge),
			float(upper_edge),
		])

		desired.extend([
			1.0 / float(cic_magnitude(lower_edge)),
			1.0 / float(cic_magnitude(upper_edge)),
		])

		weights.append(PASSBAND_WEIGHT)

	bands.extend([
		STOPBAND_START,
		FS_OUTPUT / 2,
	])

	desired.extend([
		0.0,
		0.0,
	])

	weights.append(STOPBAND_WEIGHT)

	return bands, desired, weights


def design_floating_coefficients() -> np.ndarray:
	"""Design the floating-point CIC compensation FIR."""
	bands, desired, weights = build_firls_specification()

	return firls(
		TAPS,
		bands,
		desired,
		weight=weights,
		fs=FS_OUTPUT,
	)


def round_half_away_from_zero(
	values: np.ndarray,
) -> np.ndarray:
	"""Round to nearest integers, with exact ties away from zero."""
	values = np.asarray(values, dtype=float)

	return np.where(
		values >= 0,
		np.floor(values + 0.5),
		np.ceil(values - 0.5),
	).astype(np.int64)


def quantize_coefficients(
	floating_coefficients: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
	"""Quantize coefficients to signed 18-bit integers with 17 fractional bits."""
	coefficient_integers = round_half_away_from_zero(
		floating_coefficients * COEFFICIENT_SCALE
	)

	minimum = -(1 << (COEFFICIENT_WIDTH - 1))
	maximum = (1 << (COEFFICIENT_WIDTH - 1)) - 1

	if np.any(coefficient_integers < minimum):
		raise ValueError(
			"a quantized coefficient is below the signed range"
		)

	if np.any(coefficient_integers > maximum):
		raise ValueError(
			"a quantized coefficient is above the signed range"
		)

	quantized_coefficients = (
		coefficient_integers.astype(float)
		/ COEFFICIENT_SCALE
	)

	return coefficient_integers, quantized_coefficients


def measure_combined_response(
	coefficients: np.ndarray,
) -> dict[str, float]:
	"""Measure the combined CIC and FIR frequency response."""
	frequencies, fir_response = freqz(
		coefficients,
		worN=RESPONSE_POINTS,
		fs=FS_OUTPUT,
	)

	combined_magnitude = (
		np.abs(fir_response)
		* cic_magnitude(frequencies)
	)

	combined_db = 20 * np.log10(
		np.maximum(
			combined_magnitude,
			np.finfo(float).tiny,
		)
	)

	passband = frequencies <= PASSBAND_EDGE
	stopband = frequencies >= STOPBAND_START

	passband_values = combined_db[passband]
	stopband_values = combined_db[stopband]

	return {
		"passband_min_db": float(
			np.min(passband_values)
		),
		"passband_max_db": float(
			np.max(passband_values)
		),
		"passband_ripple_db": float(
			np.ptp(passband_values)
		),
		"stopband_max_db": float(
			np.max(stopband_values)
		),
		"dc_gain": float(
			combined_magnitude[0]
		),
	}


def verify_design(
	floating_coefficients: np.ndarray,
	coefficient_integers: np.ndarray,
	quantized_coefficients: np.ndarray,
	floating_metrics: dict[str, float],
	quantized_metrics: dict[str, float],
) -> None:
	"""Fail if the designed filter violates the frozen contract."""
	assert len(floating_coefficients) == TAPS
	assert len(coefficient_integers) == TAPS
	assert len(quantized_coefficients) == TAPS

	assert np.allclose(
		floating_coefficients,
		floating_coefficients[::-1],
		atol=1e-15,
	)

	assert np.array_equal(
		coefficient_integers,
		coefficient_integers[::-1],
	)

	for metrics in (
		floating_metrics,
		quantized_metrics,
	):
		assert (
			metrics["passband_min_db"]
			>= -PASSBAND_LIMIT_DB
		)

		assert (
			metrics["passband_max_db"]
			<= PASSBAND_LIMIT_DB
		)

		assert (
			metrics["stopband_max_db"]
			<= STOPBAND_TARGET_DB
		)

	assert np.isclose(
		cic_magnitude(0),
		512.0,
	)

	assert np.isclose(
		cic_magnitude(100_000),
		496.2940637508942,
	)

	assert np.isclose(
		cic_magnitude(200_000),
		451.6404975705644,
	)


def print_metrics(
	name: str,
	metrics: dict[str, float],
) -> None:
	"""Print one response summary."""
	print(f"{name} response")

	print(
		f"  DC gain:          "
		f"{metrics['dc_gain']:.9f}"
	)

	print(
		f"  Passband minimum: "
		f"{metrics['passband_min_db']:.6f} dB"
	)

	print(
		f"  Passband maximum: "
		f"{metrics['passband_max_db']:.6f} dB"
	)

	print(
		f"  Passband ripple:  "
		f"{metrics['passband_ripple_db']:.6f} dB"
	)

	print(
		f"  Stopband maximum: "
		f"{metrics['stopband_max_db']:.6f} dB"
	)


def main() -> None:
	"""Design, quantize, verify, and report the FIR coefficients."""
	floating_coefficients = design_floating_coefficients()

	(
		coefficient_integers,
		quantized_coefficients,
	) = quantize_coefficients(
		floating_coefficients
	)

	floating_metrics = measure_combined_response(
		floating_coefficients
	)

	quantized_metrics = measure_combined_response(
		quantized_coefficients
	)

	verify_design(
		floating_coefficients,
		coefficient_integers,
		quantized_coefficients,
		floating_metrics,
		quantized_metrics,
	)

	print("CIC sanity checks")

	for frequency in (
		0,
		100_000,
		200_000,
	):
		magnitude = float(
			cic_magnitude(frequency)
		)

		normalized_db = 20 * np.log10(
			magnitude / 512
		)

		print(
			f"  {frequency:>7} Hz: "
			f"magnitude={magnitude:.6f}, "
			f"normalized={normalized_db:.6f} dB"
		)

	print()

	print_metrics(
		"Floating-point",
		floating_metrics,
	)

	print()

	print_metrics(
		"Quantized Q17",
		quantized_metrics,
	)

	print()
	print("Quantized coefficient integers")
	print(coefficient_integers.tolist())

	print()

	print(
		"Integer coefficient sum: "
		f"{int(np.sum(coefficient_integers))}"
	)

	print(
		"Represented coefficient sum: "
		f"{float(np.sum(quantized_coefficients)):.12f}"
	)

	print("Design contract: PASS")


if __name__ == "__main__":
	main()
