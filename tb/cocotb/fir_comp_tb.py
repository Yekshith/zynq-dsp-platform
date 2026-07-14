"""Bit-exact cocotb verification for the FIR compensation RTL."""

import sys
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge

REPO_ROOT = Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
	sys.path.insert(0, str(REPO_ROOT))

from model.fir import FIRCompensator
from model.fir_coefficients import (
	COEFFICIENT_SCALE,
	FIR_COEFFICIENTS_Q17,
	TAPS,
)
from model.stimulus import impulse, sine, step


CLOCK_PERIOD_NS = 10
INPUT_WIDTH = 21
FS_FIR = 1_250_000


def encode_signed(value: int, width: int) -> int:
	"""Return the two's-complement bit pattern for a signed integer."""
	return value & ((1 << width) - 1)


async def reset_dut(dut) -> None:
	"""Apply synchronous reset and clear the FIR input controls."""
	dut.rst.value = 1
	dut.in_valid.value = 0
	dut.in_sample.value = 0

	for _ in range(3):
		await RisingEdge(dut.clk)

	await FallingEdge(dut.clk)
	dut.rst.value = 0

	await RisingEdge(dut.clk)
	await ReadOnly()

	assert int(dut.out_valid.value) == 0
	assert dut.out_sample.value.signed_integer == 0


async def apply_cycle(
	dut,
	model: FIRCompensator,
	sample: int,
	valid: bool,
) -> int | None:
	"""Drive one FIR cycle and compare it against the Python model."""
	await FallingEdge(dut.clk)

	dut.in_valid.value = int(valid)
	dut.in_sample.value = encode_signed(
		sample,
		INPUT_WIDTH,
	)

	await RisingEdge(dut.clk)
	await ReadOnly()

	if not valid:
		assert int(dut.out_valid.value) == 0
		return None

	expected = model.process_sample(sample)

	assert int(dut.out_valid.value) == 1

	actual = dut.out_sample.value.signed_integer

	assert actual == expected

	return actual


async def run_vector(
	dut,
	samples: list[int],
	insert_stalls: bool = False,
) -> tuple[list[int], list[int]]:
	"""Reset the DUT and compare a complete deterministic FIR vector."""
	await reset_dut(dut)

	model = FIRCompensator()

	expected_outputs: list[int] = []
	actual_outputs: list[int] = []

	for index, sample in enumerate(samples):
		if insert_stalls and index % 5 == 0:
			result = await apply_cycle(
				dut=dut,
				model=model,
				sample=0,
				valid=False,
			)

			assert result is None

		expected = model.process_sample(sample)

		await FallingEdge(dut.clk)

		dut.in_valid.value = 1
		dut.in_sample.value = encode_signed(
			sample,
			INPUT_WIDTH,
		)

		await RisingEdge(dut.clk)
		await ReadOnly()

		assert int(dut.out_valid.value) == 1

		actual = dut.out_sample.value.signed_integer

		assert actual == expected

		expected_outputs.append(expected)
		actual_outputs.append(actual)

	await FallingEdge(dut.clk)
	dut.in_valid.value = 0
	dut.in_sample.value = 0

	return expected_outputs, actual_outputs


@cocotb.test()
async def fir_comp_matches_golden_model(dut):
	"""Replay shared vectors with zero-tolerance FIR comparison."""
	cocotb.start_soon(
		Clock(
			dut.clk,
			CLOCK_PERIOD_NS,
			units="ns",
		).start()
	)

	vectors = [
		(
			"scaled impulse",
			impulse(
				length=TAPS,
				amplitude=COEFFICIENT_SCALE,
			),
		),
		(
			"positive normalization step",
			step(
				length=64,
				amplitude=512,
			),
		),
		(
			"negative normalization step",
			step(
				length=64,
				amplitude=-512,
			),
		),
		(
			"positive input boundary",
			step(
				length=64,
				amplitude=1_048_575,
			),
		),
		(
			"negative input boundary",
			step(
				length=64,
				amplitude=-1_048_576,
			),
		),
		(
			"in-band sine",
			sine(
				fs=FS_FIR,
				f0=100_000,
				amplitude=1_000_000,
				count=256,
			),
		),
	]

	for name, samples in vectors:
		dut._log.info("Running FIR vector: %s", name)

		expected, actual = await run_vector(
			dut=dut,
			samples=samples,
		)

		assert actual == expected
		assert len(actual) == len(samples)

		if name == "scaled impulse":
			assert actual == list(
				FIR_COEFFICIENTS_Q17
			)

		if name == "positive normalization step":
			assert actual[30:] == [
				1
			] * (len(actual) - 30)

		if name == "negative normalization step":
			assert actual[30:] == [
				-1
			] * (len(actual) - 30)

	stall_samples = sine(
		fs=FS_FIR,
		f0=78_125,
		amplitude=900_000,
		count=128,
	)

	expected, actual = await run_vector(
		dut=dut,
		samples=stall_samples,
		insert_stalls=True,
	)

	assert actual == expected
	assert len(actual) == len(stall_samples)
