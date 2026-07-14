"""Bit-exact cocotb verification for the CIC-to-FIR RTL pipeline."""

import sys
from collections import deque
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge

REPO_ROOT = Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
	sys.path.insert(0, str(REPO_ROOT))

from model.pipeline import CICFIRPipeline
from model.stimulus import impulse, sine, step


CLOCK_PERIOD_NS = 10
INPUT_WIDTH = 12
DECIMATION_FACTOR = 8
FS_INPUT = 10_000_000


def encode_signed(value: int, width: int) -> int:
	"""Return the two's-complement bit pattern for a signed integer."""
	return value & ((1 << width) - 1)


async def reset_dut(dut) -> None:
	"""Apply synchronous reset and clear the pipeline input."""
	await FallingEdge(dut.clk)

	dut.rst.value = 1
	dut.in_valid.value = 0
	dut.in_sample.value = 0

	for _ in range(3):
		await RisingEdge(dut.clk)

	await FallingEdge(dut.clk)

	dut.rst.value = 0
	dut.in_valid.value = 0
	dut.in_sample.value = 0

	await RisingEdge(dut.clk)
	await ReadOnly()

	assert int(dut.out_valid.value) == 0
	assert dut.out_sample.value.signed_integer == 0


async def run_clock_cycle(
	dut,
	model: CICFIRPipeline,
	pending_outputs: deque[int],
	expected_outputs: list[int],
	actual_outputs: list[int],
	sample: int = 0,
	valid: bool = False,
) -> None:
	"""Drive and verify one complete pipeline clock cycle."""
	await FallingEdge(dut.clk)

	dut.in_valid.value = int(valid)
	dut.in_sample.value = encode_signed(
		sample,
		INPUT_WIDTH,
	)

	await RisingEdge(dut.clk)
	await ReadOnly()

	actual_valid = int(dut.out_valid.value)

	if actual_valid == 1:
		assert pending_outputs, (
			"RTL produced an output when no model output was pending"
		)

		expected = pending_outputs.popleft()
		actual = dut.out_sample.value.signed_integer

		assert actual == expected

		actual_outputs.append(actual)

	elif pending_outputs:
		assert len(pending_outputs) <= 1

	if valid:
		expected = model.process_sample(sample)

		if expected is not None:
			pending_outputs.append(expected)
			expected_outputs.append(expected)


async def run_vector(
	dut,
	samples: list[int],
	insert_stalls: bool = False,
) -> tuple[list[int], list[int]]:
	"""Reset and compare one deterministic pipeline stimulus vector."""
	await reset_dut(dut)

	model = CICFIRPipeline()

	pending_outputs: deque[int] = deque()
	expected_outputs: list[int] = []
	actual_outputs: list[int] = []

	for index, sample in enumerate(samples):
		if insert_stalls and index % 7 == 0:
			await run_clock_cycle(
				dut=dut,
				model=model,
				pending_outputs=pending_outputs,
				expected_outputs=expected_outputs,
				actual_outputs=actual_outputs,
				valid=False,
			)

		await run_clock_cycle(
			dut=dut,
			model=model,
			pending_outputs=pending_outputs,
			expected_outputs=expected_outputs,
			actual_outputs=actual_outputs,
			sample=sample,
			valid=True,
		)

	flush_cycles = 0

	while pending_outputs:
		await run_clock_cycle(
			dut=dut,
			model=model,
			pending_outputs=pending_outputs,
			expected_outputs=expected_outputs,
			actual_outputs=actual_outputs,
			valid=False,
		)

		flush_cycles += 1

		assert flush_cycles <= 4

	await run_clock_cycle(
		dut=dut,
		model=model,
		pending_outputs=pending_outputs,
		expected_outputs=expected_outputs,
		actual_outputs=actual_outputs,
		valid=False,
	)

	assert not pending_outputs

	# Leave the simulator in a writable phase before the next vector.
	await FallingEdge(dut.clk)

	dut.in_valid.value = 0
	dut.in_sample.value = 0

	return expected_outputs, actual_outputs


@cocotb.test()
async def cic_fir_pipeline_matches_golden_model(dut):
	"""Replay shared vectors with zero-tolerance pipeline comparison."""
	cocotb.start_soon(
		Clock(
			dut.clk,
			CLOCK_PERIOD_NS,
			units="ns",
		).start()
	)

	vectors = [
		(
			"impulse",
			impulse(
				length=512,
				amplitude=1,
			),
		),
		(
			"unit step",
			step(
				length=1024,
				amplitude=1,
			),
		),
		(
			"positive full scale",
			step(
				length=4096,
				amplitude=2047,
			),
		),
		(
			"negative full scale",
			step(
				length=4096,
				amplitude=-2048,
			),
		),
		(
			"in-band sine",
			sine(
				fs=FS_INPUT,
				f0=100_000,
				amplitude=1000,
				count=4096,
			),
		),
	]

	for name, samples in vectors:
		dut._log.info(
			"Running pipeline vector: %s",
			name,
		)

		expected, actual = await run_vector(
			dut=dut,
			samples=samples,
		)

		assert actual == expected

		assert len(actual) == (
			len(samples) // DECIMATION_FACTOR
		)

		if name == "unit step":
			assert actual[32:] == [
				1
			] * (len(actual) - 32)

		if name == "positive full scale":
			assert actual[32:] == [
				2055
			] * (len(actual) - 32)

		if name == "negative full scale":
			assert actual[32:] == [
				-2056
			] * (len(actual) - 32)

	stall_samples = sine(
		fs=FS_INPUT,
		f0=78_125,
		amplitude=1000,
		count=1024,
	)

	expected, actual = await run_vector(
		dut=dut,
		samples=stall_samples,
		insert_stalls=True,
	)

	assert actual == expected

	assert len(actual) == (
		len(stall_samples)
		// DECIMATION_FACTOR
	)