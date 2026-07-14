"""Frequency-response tests for the FIR coefficient design."""

import numpy as np

from model.fir_coefficients import (
	COEFFICIENT_SCALE,
	COEFFICIENT_WIDTH,
	FIR_COEFFICIENTS_Q17,
	TAPS,
)
from scripts.design_fir import (
	PASSBAND_LIMIT_DB,
	STOPBAND_TARGET_DB,
	design_floating_coefficients,
	measure_combined_response,
	quantize_coefficients,
)


def test_design_reproduces_frozen_coefficients():
	"""Ensure the design script reproduces the committed Q17 coefficients."""
	floating_coefficients = design_floating_coefficients()

	coefficient_integers, _ = quantize_coefficients(
		floating_coefficients
	)

	assert coefficient_integers.tolist() == list(
		FIR_COEFFICIENTS_Q17
	)


def test_floating_coefficients_are_symmetric():
	"""Check the floating-point Type-I linear-phase coefficient symmetry."""
	coefficients = design_floating_coefficients()

	assert len(coefficients) == TAPS

	assert np.allclose(
		coefficients,
		coefficients[::-1],
		atol=1e-15,
	)


def test_quantized_coefficients_are_symmetric_and_in_range():
	"""Check coefficient symmetry and signed 18-bit range compliance."""
	minimum = -(1 << (COEFFICIENT_WIDTH - 1))
	maximum = (1 << (COEFFICIENT_WIDTH - 1)) - 1

	assert (
		FIR_COEFFICIENTS_Q17
		== FIR_COEFFICIENTS_Q17[::-1]
	)

	assert all(
		minimum <= coefficient <= maximum
		for coefficient in FIR_COEFFICIENTS_Q17
	)


def test_floating_combined_response_meets_contract():
	"""Check the ideal CIC-to-FIR response against the frozen limits."""
	coefficients = design_floating_coefficients()

	metrics = measure_combined_response(
		coefficients
	)

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


def test_quantized_combined_response_meets_contract():
	"""Check the committed Q17 response against the frozen limits."""
	quantized_coefficients = (
		np.asarray(
			FIR_COEFFICIENTS_Q17,
			dtype=float,
		)
		/ COEFFICIENT_SCALE
	)

	metrics = measure_combined_response(
		quantized_coefficients
	)

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


def test_quantized_response_tracks_floating_response():
	"""Bound the response degradation introduced by Q17 quantization."""
	floating_coefficients = design_floating_coefficients()

	_, quantized_coefficients = quantize_coefficients(
		floating_coefficients
	)

	floating_metrics = measure_combined_response(
		floating_coefficients
	)

	quantized_metrics = measure_combined_response(
		quantized_coefficients
	)

	assert abs(
		quantized_metrics["dc_gain"]
		- floating_metrics["dc_gain"]
	) < 0.005

	assert (
		quantized_metrics["passband_ripple_db"]
		- floating_metrics["passband_ripple_db"]
	) < 0.20

	assert abs(
		quantized_metrics["stopband_max_db"]
		- floating_metrics["stopband_max_db"]
	) < 1.0