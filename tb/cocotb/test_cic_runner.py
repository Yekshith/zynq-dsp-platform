"""Pytest runner for the CIC decimator cocotb testbench."""

import os
from pathlib import Path

from cocotb.runner import get_runner


REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = REPO_ROOT / "tb" / "cocotb"
BUILD_DIR = REPO_ROOT / "sim_build" / "cic_decimator"


def test_cic_decimator_runner():
	"""Compile the CIC RTL and execute its cocotb regression."""
	simulator = os.getenv("SIM", "ghdl")
	waves_enabled = os.getenv("WAVES", "0") == "1"

	python_paths = [
		str(REPO_ROOT),
		str(TEST_DIR),
	]

	existing_python_path = os.getenv("PYTHONPATH")

	if existing_python_path:
		python_paths.append(existing_python_path)

	runner = get_runner(simulator)

	runner.build(
		vhdl_sources=[
			REPO_ROOT / "rtl" / "cic_decimator.vhd",
		],
		hdl_toplevel="cic_decimator",
		build_args=[
			"--std=08",
		],
		build_dir=BUILD_DIR,
		always=True,
		waves=waves_enabled,
	)

	runner.test(
		hdl_toplevel="cic_decimator",
		hdl_toplevel_lang="vhdl",
		test_module="cic_decimator_tb",
		build_dir=BUILD_DIR,
		extra_env={
			"PYTHONPATH": os.pathsep.join(
				python_paths
			),
		},
		waves=waves_enabled,
	)


if __name__ == "__main__":
	test_cic_decimator_runner()