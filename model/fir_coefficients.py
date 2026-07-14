"""Frozen FIR compensation coefficients for project release v0.1."""


TAPS = 31

COEFFICIENT_WIDTH = 18
FRACTIONAL_BITS = 17
COEFFICIENT_SCALE = 1 << FRACTIONAL_BITS


FIR_COEFFICIENTS_Q17: tuple[int, ...] = (
	0,
	0,
	0,
	-1,
	0,
	3,
	2,
	-5,
	-5,
	8,
	12,
	-10,
	-29,
	6,
	84,
	127,
	84,
	6,
	-29,
	-10,
	12,
	8,
	-5,
	-5,
	2,
	3,
	0,
	-1,
	0,
	0,
	0,
)


def coefficients_as_float() -> list[float]:
	"""Return the frozen Q17 coefficients as floating-point values."""
	return [
		coefficient / COEFFICIENT_SCALE
		for coefficient in FIR_COEFFICIENTS_Q17
	]
