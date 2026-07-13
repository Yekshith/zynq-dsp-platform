import numpy as np
import pytest

from model.cic import CICDecimator, wrap_signed
from model.stimulus import impulse, sine, step


def test_wrap_signed_known_cases():
	"""Check basic in-range, boundary, and overflow behaviour using 4 bits."""
	assert wrap_signed(0, 4) == 0
	assert wrap_signed(3, 4) == 3
	assert wrap_signed(-3, 4) == -3

	assert wrap_signed(7, 4) == 7
	assert wrap_signed(-8, 4) == -8

	assert wrap_signed(8, 4) == -8
	assert wrap_signed(9, 4) == -7
	assert wrap_signed(15, 4) == -1
	assert wrap_signed(16, 4) == 0
	assert wrap_signed(17, 4) == 1

	assert wrap_signed(-9, 4) == 7
	assert wrap_signed(-10, 4) == 6
	assert wrap_signed(-16, 4) == 0
	assert wrap_signed(-17, 4) == -1


def test_wrap_signed_21_bit_boundaries():
	"""Check the exact signed limits used by the CIC implementation."""
	width = 21
	maximum = (1 << 20) - 1
	minimum = -(1 << 20)
	modulus = 1 << width

	assert wrap_signed(maximum, width) == maximum
	assert wrap_signed(minimum, width) == minimum
	assert wrap_signed(1 << 20, width) == minimum
	assert wrap_signed(minimum - 1, width) == maximum

	multi_wrap_value = (11 * modulus) + (1 << 20) + 77
	assert wrap_signed(multi_wrap_value, width) == minimum + 77


def test_cic_initial_state():
	"""Check that construction places every state element at zero."""
	cic = CICDecimator()

	assert cic.integrators == [0, 0, 0]
	assert cic.comb_delays == [[0], [0], [0]]
	assert cic.counter == 0


def test_cic_integrator_progression():
	"""Check that every stage uses the newly updated previous-stage result."""
	cic = CICDecimator()

	assert cic.process_sample(1) is None
	assert cic.integrators == [1, 1, 1]

	assert cic.process_sample(1) is None
	assert cic.integrators == [2, 3, 4]

	assert cic.process_sample(1) is None
	assert cic.integrators == [3, 6, 10]


def test_cic_rejects_out_of_range_input():
	"""Reject values that cannot be represented by the signed 12-bit input."""
	cic = CICDecimator()

	with pytest.raises(ValueError):
		cic.process_sample(2048)

	with pytest.raises(ValueError):
		cic.process_sample(-2049)


def test_cic_first_step_output():
	"""Check output timing and the first startup-transient value."""
	cic = CICDecimator()

	for sample in step(7):
		assert cic.process_sample(sample) is None

	assert cic.process_sample(1) == 120
	assert cic.counter == 0


def test_cic_output_count():
	"""Check that floor(input_count / R) output samples are produced."""
	cic = CICDecimator()
	outputs = []

	for sample in step(25):
		result = cic.process_sample(sample)

		if result is not None:
			outputs.append(result)

	assert len(outputs) == 25 // cic.r
	assert len(outputs) == 3


def test_cic_impulse_response():
	"""Check the frozen decimated impulse response and decimation phase."""
	cic = CICDecimator()
	outputs = []

	for sample in impulse(32):
		result = cic.process_sample(sample)

		if result is not None:
			outputs.append(result)

	assert outputs == [36, 28, 0, 0]


def test_cic_step_response_reaches_dc_gain():
	"""Check startup transient and steady-state CIC gain for a unit step."""
	cic = CICDecimator()
	outputs = []

	for sample in step(40):
		result = cic.process_sample(sample)

		if result is not None:
			outputs.append(result)

	assert outputs == [120, 456, 512, 512, 512]


def test_cic_positive_full_scale_survives_internal_wrap():
	"""Prove full-scale positive output remains correct after accumulator wraps."""
	cic = CICDecimator()
	outputs = []
	stage_wrapped = [False for _ in range(cic.n)]
	input_samples = step(2048, 2047)

	for sample in input_samples:
		result = cic.process_sample(sample)

		for stage, state in enumerate(cic.integrators):
			if state < 0:
				stage_wrapped[stage] = True

		if result is not None:
			outputs.append(result)

	expected_steady_state = 2047 * 512

	assert len(outputs) == len(input_samples) // cic.r
	assert expected_steady_state == 1_048_064

	# The first two outputs are the defined startup transient.
	assert outputs[2:] == [expected_steady_state] * (len(outputs) - 2)

	# Positive accumulation can become negative only through signed wrapping.
	assert stage_wrapped == [True, True, True]


def test_cic_negative_full_scale_survives_internal_wrap():
	"""Prove the exact 21-bit floor remains correct after accumulator wraps."""
	cic = CICDecimator()
	outputs = []
	stage_wrapped = [False for _ in range(cic.n)]
	input_samples = step(2048, -2048)

	for sample in input_samples:
		result = cic.process_sample(sample)

		for stage, state in enumerate(cic.integrators):
			if state > 0:
				stage_wrapped[stage] = True

		if result is not None:
			outputs.append(result)

	expected_steady_state = -2048 * 512

	assert len(outputs) == len(input_samples) // cic.r
	assert expected_steady_state == -1_048_576

	# The first two outputs are the defined startup transient.
	assert outputs[2:] == [expected_steady_state] * (len(outputs) - 2)

	# Negative accumulation can become positive only through signed wrapping.
	assert stage_wrapped == [True, True, True]


def test_cic_sine_preserves_frequency():
	"""Check output count and tone frequency after decimation."""
	fs_input = 10_000_000
	tone_frequency = 100_000
	amplitude = 1000
	sample_count = 1600

	input_samples = sine(
		fs=fs_input,
		f0=tone_frequency,
		amplitude=amplitude,
		count=sample_count,
	)

	cic = CICDecimator()
	outputs = []

	for sample in input_samples:
		result = cic.process_sample(sample)

		if result is not None:
			outputs.append(result)

	assert len(outputs) == sample_count // cic.r

	output_array = np.asarray(outputs, dtype=float)
	output_sample_rate = fs_input / cic.r

	spectrum = np.abs(np.fft.rfft(output_array))
	frequencies = np.fft.rfftfreq(
		len(output_array),
		d=1 / output_sample_rate,
	)

	# Ignore DC when locating the sine-wave spectral peak.
	spectrum[0] = 0

	peak_index = int(np.argmax(spectrum))
	measured_frequency = frequencies[peak_index]
	fft_bin_width = output_sample_rate / len(output_array)

	assert abs(measured_frequency - tone_frequency) <= fft_bin_width