"""Bit-exact fixed-point FIR compensation model."""

from collections.abc import Iterable, Sequence

from model.cic import wrap_signed
from model.fir_coefficients import (
	COEFFICIENT_WIDTH,
	FIR_COEFFICIENTS_Q17,
	FRACTIONAL_BITS,
	TAPS,
)


def round_shift_half_away_from_zero(
	value: int,
	fractional_bits: int,
) -> int:
	"""Round and remove fractional bits, with exact ties away from zero."""
	if fractional_bits < 0:
		raise ValueError("fractional_bits must not be negative")

	if fractional_bits == 0:
		return value

	rounding_offset = 1 << (fractional_bits - 1)

	if value >= 0:
		return (value + rounding_offset) >> fractional_bits

	return -(
		((-value) + rounding_offset)
		>> fractional_bits
	)


def saturate_signed(value: int, width: int) -> int:
	"""Saturate an integer to the range of a signed value of the given width."""
	if width <= 0:
		raise ValueError("width must be greater than zero")

	minimum = -(1 << (width - 1))
	maximum = (1 << (width - 1)) - 1

	if value > maximum:
		return maximum

	if value < minimum:
		return minimum

	return value


class FIRCompensator:
	"""Direct-form fixed-point FIR compensation filter."""

	def __init__(
		self,
		coefficients: Sequence[int] = FIR_COEFFICIENTS_Q17,
		input_width: int = 21,
		coefficient_width: int = COEFFICIENT_WIDTH,
		fractional_bits: int = FRACTIONAL_BITS,
		product_width: int = 39,
		accumulator_width: int = 44,
		output_width: int = 16,
	) -> None:
		if input_width <= 0:
			raise ValueError("input_width must be greater than zero")

		if coefficient_width <= 0:
			raise ValueError(
				"coefficient_width must be greater than zero"
			)

		if fractional_bits < 0:
			raise ValueError(
				"fractional_bits must not be negative"
			)

		if product_width <= 0:
			raise ValueError(
				"product_width must be greater than zero"
			)

		if accumulator_width <= 0:
			raise ValueError(
				"accumulator_width must be greater than zero"
			)

		if output_width <= 0:
			raise ValueError(
				"output_width must be greater than zero"
			)

		if len(coefficients) != TAPS:
			raise ValueError(
				f"exactly {TAPS} coefficients are required"
			)

		minimum_coefficient = -(
			1 << (coefficient_width - 1)
		)

		maximum_coefficient = (
			1 << (coefficient_width - 1)
		) - 1

		for coefficient in coefficients:
			if (
				coefficient < minimum_coefficient
				or coefficient > maximum_coefficient
			):
				raise ValueError(
					"coefficient is outside the signed "
					f"{coefficient_width}-bit range"
				)

		self.coefficients = tuple(coefficients)
		self.input_width = input_width
		self.coefficient_width = coefficient_width
		self.fractional_bits = fractional_bits
		self.product_width = product_width
		self.accumulator_width = accumulator_width
		self.output_width = output_width

		self.reset()

	def reset(self) -> None:
		"""Clear the FIR sample history."""
		self.samples = [
			0
			for _ in range(len(self.coefficients))
		]

	def process_sample(self, sample: int) -> int:
		"""Process one signed CIC output sample."""
		minimum_input = -(
			1 << (self.input_width - 1)
		)

		maximum_input = (
			1 << (self.input_width - 1)
		) - 1

		if sample < minimum_input or sample > maximum_input:
			raise ValueError(
				f"sample must be between "
				f"{minimum_input} and {maximum_input}"
			)

		self.samples.pop()
		self.samples.insert(0, sample)

		accumulator = 0

		for sample_value, coefficient in zip(
			self.samples,
			self.coefficients,
		):
			product = wrap_signed(
				sample_value * coefficient,
				self.product_width,
			)

			accumulator = wrap_signed(
				accumulator + product,
				self.accumulator_width,
			)

		scaled_result = round_shift_half_away_from_zero(
			accumulator,
			self.fractional_bits,
		)

		return saturate_signed(
			scaled_result,
			self.output_width,
		)

	def process(
		self,
		samples: Iterable[int],
	) -> list[int]:
		"""Process a sequence of input samples."""
		return [
			self.process_sample(sample)
			for sample in samples
		]
