"""Tests for the fixed-point FIR compensation model."""

import pytest

from model.fir import (
	FIRCompensator,
	round_shift_half_away_from_zero,
	saturate_signed,
)
from model.fir_coefficients import (
	COEFFICIENT_SCALE,
	COEFFICIENT_WIDTH,
	FIR_COEFFICIENTS_Q17,
	FRACTIONAL_BITS,
	TAPS,
)
from model.stimulus import impulse, step


def test_fir_coefficient_contract():
	"""Check the frozen coefficient count, symmetry, and range."""
	minimum = -(1 << (COEFFICIENT_WIDTH - 1))
	maximum = (1 << (COEFFICIENT_WIDTH - 1)) - 1

	assert len(FIR_COEFFICIENTS_Q17) == TAPS

	assert (
		FIR_COEFFICIENTS_Q17
		== FIR_COEFFICIENTS_Q17[::-1]
	)

	assert all(
		minimum <= coefficient <= maximum
		for coefficient in FIR_COEFFICIENTS_Q17
	)

	assert sum(FIR_COEFFICIENTS_Q17) == 257


def test_round_shift_half_away_from_zero():
	"""Check positive and negative rounding around half-way cases."""
	assert round_shift_half_away_from_zero(0, 3) == 0

	assert round_shift_half_away_from_zero(11, 3) == 1
	assert round_shift_half_away_from_zero(12, 3) == 2
	assert round_shift_half_away_from_zero(13, 3) == 2

	assert round_shift_half_away_from_zero(-11, 3) == -1
	assert round_shift_half_away_from_zero(-12, 3) == -2
	assert round_shift_half_away_from_zero(-13, 3) == -2

	assert round_shift_half_away_from_zero(17, 0) == 17
	assert round_shift_half_away_from_zero(-17, 0) == -17


def test_round_shift_rejects_negative_fractional_width():
	"""Reject an invalid negative fractional-bit count."""
	with pytest.raises(ValueError):
		round_shift_half_away_from_zero(
			value=100,
			fractional_bits=-1,
		)


def test_saturate_signed_known_cases():
	"""Check in-range values and both 16-bit saturation boundaries."""
	assert saturate_signed(0, 16) == 0
	assert saturate_signed(1234, 16) == 1234
	assert saturate_signed(-1234, 16) == -1234

	assert saturate_signed(32767, 16) == 32767
	assert saturate_signed(-32768, 16) == -32768

	assert saturate_signed(32768, 16) == 32767
	assert saturate_signed(100000, 16) == 32767

	assert saturate_signed(-32769, 16) == -32768
	assert saturate_signed(-100000, 16) == -32768


def test_saturate_signed_rejects_invalid_width():
	"""Reject zero and negative output widths."""
	with pytest.raises(ValueError):
		saturate_signed(0, 0)

	with pytest.raises(ValueError):
		saturate_signed(0, -1)


def test_fir_initial_state():
	"""Check that all sample-history registers start at zero."""
	fir = FIRCompensator()

	assert len(fir.samples) == TAPS
	assert fir.samples == [0] * TAPS


def test_fir_reset_clears_sample_history():
	"""Check that reset removes all previously processed samples."""
	fir = FIRCompensator()

	fir.process_sample(1000)
	fir.process_sample(-500)

	assert fir.samples != [0] * TAPS

	fir.reset()

	assert fir.samples == [0] * TAPS


def test_fir_rejects_out_of_range_input():
	"""Reject values outside the signed 21-bit CIC-output range."""
	fir = FIRCompensator()

	with pytest.raises(ValueError):
		fir.process_sample(1_048_576)

	with pytest.raises(ValueError):
		fir.process_sample(-1_048_577)


def test_fir_accepts_input_boundaries():
	"""Accept the exact positive and negative 21-bit boundaries."""
	fir = FIRCompensator()

	fir.process_sample(1_048_575)

	fir.reset()

	fir.process_sample(-1_048_576)


def test_fir_rejects_wrong_coefficient_count():
	"""Require exactly 31 coefficients."""
	with pytest.raises(ValueError):
		FIRCompensator(
			coefficients=(1, 2, 3),
		)


def test_fir_rejects_coefficient_above_range():
	"""Reject a coefficient above the signed 18-bit maximum."""
	coefficients = [0] * TAPS
	coefficients[0] = 1 << 17

	with pytest.raises(ValueError):
		FIRCompensator(
			coefficients=coefficients,
		)


def test_fir_rejects_coefficient_below_range():
	"""Reject a coefficient below the signed 18-bit minimum."""
	coefficients = [0] * TAPS
	coefficients[0] = -(1 << 17) - 1

	with pytest.raises(ValueError):
		FIRCompensator(
			coefficients=coefficients,
		)


def test_fir_impulse_response_matches_coefficients():
	"""Recover the stored Q17 coefficients using a scaled impulse."""
	fir = FIRCompensator()

	input_samples = impulse(
		length=TAPS,
		amplitude=COEFFICIENT_SCALE,
	)

	outputs = fir.process(input_samples)

	assert outputs == list(FIR_COEFFICIENTS_Q17)


def test_fir_group_delay():
	"""Check that the largest impulse-response tap occurs at sample 15."""
	fir = FIRCompensator()

	outputs = fir.process(
		impulse(
			length=TAPS,
			amplitude=COEFFICIENT_SCALE,
		)
	)

	peak_index = max(
		range(len(outputs)),
		key=lambda index: outputs[index],
	)

	assert peak_index == 15
	assert outputs[peak_index] == 127


def test_fir_normalizes_cic_unit_step_gain():
	"""Check that a steady CIC value of 512 returns approximately one."""
	fir = FIRCompensator()

	outputs = fir.process(
		step(
			length=64,
			amplitude=512,
		)
	)

	assert outputs[30:] == [1] * (64 - 30)


def test_fir_normalizes_negative_cic_unit_step_gain():
	"""Check signed normalization for a steady CIC value of minus 512."""
	fir = FIRCompensator()

	outputs = fir.process(
		step(
			length=64,
			amplitude=-512,
		)
	)

	assert outputs[30:] == [-1] * (64 - 30)


def test_fir_positive_output_saturation():
	"""Force a result above the positive 16-bit output limit."""
	maximum_coefficient = (
		1 << (COEFFICIENT_WIDTH - 1)
	) - 1

	coefficients = (
		maximum_coefficient,
	) + (0,) * (TAPS - 1)

	fir = FIRCompensator(
		coefficients=coefficients,
	)

	output = fir.process_sample(1_048_575)

	assert output == 32767


def test_fir_negative_output_saturation():
	"""Force a result below the negative 16-bit output limit."""
	maximum_coefficient = (
		1 << (COEFFICIENT_WIDTH - 1)
	) - 1

	coefficients = (
		maximum_coefficient,
	) + (0,) * (TAPS - 1)

	fir = FIRCompensator(
		coefficients=coefficients,
	)

	output = fir.process_sample(-1_048_576)

	assert output == -32768


def test_fir_process_output_count():
	"""Produce exactly one FIR output for each FIR input sample."""
	fir = FIRCompensator()
	input_samples = step(
		length=100,
		amplitude=512,
	)

	outputs = fir.process(input_samples)

	assert len(outputs) == len(input_samples)


def test_fir_default_fractional_width():
	"""Check that the model uses the frozen Q17 coefficient scaling."""
	fir = FIRCompensator()

	assert fir.fractional_bits == FRACTIONAL_BITS
	assert fir.fractional_bits == 17