"""Pytest runner for the FIR compensation cocotb testbench."""

import os
from pathlib import Path

from cocotb.runner import get_runner


REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = REPO_ROOT / "tb" / "cocotb"
BUILD_DIR = REPO_ROOT / "sim_build" / "fir_comp"


def test_fir_comp_runner():
	"""Compile the FIR RTL and execute its cocotb regression."""
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
			REPO_ROOT
			/ "rtl"
			/ "fir_coefficients_pkg.vhd",
			REPO_ROOT
			/ "rtl"
			/ "fir_comp.vhd",
		],
		hdl_toplevel="fir_comp",
		build_args=[
			"--std=08",
		],
		build_dir=BUILD_DIR,
		always=True,
		waves=waves_enabled,
	)

	runner.test(
		hdl_toplevel="fir_comp",
		hdl_toplevel_lang="vhdl",
		test_module="fir_comp_tb",
		build_dir=BUILD_DIR,
		extra_env={
			"PYTHONPATH": os.pathsep.join(
				python_paths
			),
		},
		waves=waves_enabled,
	)


if __name__ == "__main__":
	test_fir_comp_runner()