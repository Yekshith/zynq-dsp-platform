"""Tests for the combined CIC and FIR golden-model pipeline."""

import numpy as np

from model.cic import CICDecimator
from model.fir import FIRCompensator
from model.pipeline import CICFIRPipeline
from model.stimulus import impulse, sine, step


FS_INPUT = 10_000_000
FS_OUTPUT = 1_250_000


def test_pipeline_initial_state():
	"""Check that both filter sections begin in their reset states."""
	pipeline = CICFIRPipeline()

	assert pipeline.cic.integrators == [0, 0, 0]
	assert pipeline.cic.comb_delays == [[0], [0], [0]]
	assert pipeline.cic.counter == 0

	assert pipeline.fir.samples == [0] * 31


def test_pipeline_output_count():
	"""Produce one pipeline output for every eight ADC input samples."""
	pipeline = CICFIRPipeline()

	input_samples = step(
		length=25,
		amplitude=1,
	)

	outputs = pipeline.process(input_samples)

	assert len(outputs) == 25 // 8
	assert len(outputs) == 3


def test_pipeline_impulse_output_count():
	"""Check decimation count using a deterministic impulse stimulus."""
	pipeline = CICFIRPipeline()

	input_samples = impulse(
		length=256,
		amplitude=1,
	)

	outputs = pipeline.process(input_samples)

	assert len(outputs) == 256 // 8
	assert len(outputs) == 32


def test_pipeline_matches_separate_cic_and_fir_models():
	"""Check that the pipeline wrapper matches manual model composition."""
	input_samples = sine(
		fs=FS_INPUT,
		f0=100_000,
		amplitude=1000,
		count=2048,
	)

	pipeline = CICFIRPipeline()
	pipeline_outputs = pipeline.process(input_samples)

	cic = CICDecimator()
	fir = FIRCompensator()
	reference_outputs = []

	for sample in input_samples:
		cic_output = cic.process_sample(sample)

		if cic_output is not None:
			reference_outputs.append(
				fir.process_sample(cic_output)
			)

	assert pipeline_outputs == reference_outputs


def test_pipeline_reset_reproduces_identical_output():
	"""Check that reset restores deterministic startup behaviour."""
	pipeline = CICFIRPipeline()

	input_samples = sine(
		fs=FS_INPUT,
		f0=78_125,
		amplitude=1000,
		count=2048,
	)

	first_outputs = pipeline.process(input_samples)

	pipeline.reset()

	second_outputs = pipeline.process(input_samples)

	assert first_outputs == second_outputs


def test_pipeline_unit_step_normalization():
	"""Check that a unit ADC step settles to approximately unity."""
	pipeline = CICFIRPipeline()

	outputs = pipeline.process(
		step(
			length=1024,
			amplitude=1,
		)
	)

	assert len(outputs) == 1024 // 8

	# CIC startup occupies the first two outputs.
	# FIR history becomes fully steady after another 30 outputs.
	assert outputs[32:] == [1] * (len(outputs) - 32)


def test_pipeline_positive_full_scale_with_cic_wrap():
	"""Check positive full-scale output after all CIC stages wrap."""
	pipeline = CICFIRPipeline()
	outputs = []
	stage_wrapped = [False, False, False]

	input_samples = step(
		length=4096,
		amplitude=2047,
	)

	for sample in input_samples:
		result = pipeline.process_sample(sample)

		for stage, state in enumerate(
			pipeline.cic.integrators
		):
			if state < 0:
				stage_wrapped[stage] = True

		if result is not None:
			outputs.append(result)

	assert len(outputs) == 4096 // 8
	assert stage_wrapped == [True, True, True]

	# Quantized coefficient sum is 257 rather than the ideal 256:
	# round(2047 × 512 × 257 / 2^17) = 2055.
	assert outputs[32:] == [2055] * (len(outputs) - 32)


def test_pipeline_negative_full_scale_with_cic_wrap():
	"""Check the negative full-scale boundary after CIC wrapping."""
	pipeline = CICFIRPipeline()
	outputs = []
	stage_wrapped = [False, False, False]

	input_samples = step(
		length=4096,
		amplitude=-2048,
	)

	for sample in input_samples:
		result = pipeline.process_sample(sample)

		for stage, state in enumerate(
			pipeline.cic.integrators
		):
			if state > 0:
				stage_wrapped[stage] = True

		if result is not None:
			outputs.append(result)

	assert len(outputs) == 4096 // 8
	assert stage_wrapped == [True, True, True]

	# -2048 × 512 × 257 / 2^17 = -2056 exactly.
	assert outputs[32:] == [-2056] * (len(outputs) - 32)


def test_pipeline_sine_preserves_frequency():
	"""Check that the complete pipeline preserves an in-band tone."""
	tone_frequency = 78_125
	input_count = 8192

	input_samples = sine(
		fs=FS_INPUT,
		f0=tone_frequency,
		amplitude=1000,
		count=input_count,
	)

	pipeline = CICFIRPipeline()
	outputs = pipeline.process(input_samples)

	assert len(outputs) == input_count // 8

	# Remove the CIC and FIR startup transient before FFT analysis.
	steady_outputs = np.asarray(
		outputs[64:],
		dtype=float,
	)

	spectrum = np.abs(
		np.fft.rfft(steady_outputs)
	)

	frequencies = np.fft.rfftfreq(
		len(steady_outputs),
		d=1 / FS_OUTPUT,
	)

	spectrum[0] = 0

	peak_index = int(
		np.argmax(spectrum)
	)

	measured_frequency = frequencies[peak_index]
	fft_bin_width = FS_OUTPUT / len(steady_outputs)

	assert (
		abs(measured_frequency - tone_frequency)
		<= fft_bin_width
	)

	assert np.max(np.abs(steady_outputs)) > 0