"""Pytest runner for the complete CIC-to-FIR cocotb testbench."""

import os
from pathlib import Path

from cocotb.runner import get_runner


REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = REPO_ROOT / "tb" / "cocotb"
BUILD_DIR = REPO_ROOT / "sim_build" / "cic_fir_pipeline"


def test_cic_fir_pipeline_runner():
	"""Compile the complete RTL chain and run its cocotb regression."""
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
			/ "cic_decimator.vhd",
			REPO_ROOT
			/ "rtl"
			/ "fir_comp.vhd",
			REPO_ROOT
			/ "rtl"
			/ "cic_fir_pipeline.vhd",
		],
		hdl_toplevel="cic_fir_pipeline",
		build_args=[
			"--std=08",
		],
		build_dir=BUILD_DIR,
		always=True,
		waves=waves_enabled,
	)

	runner.test(
		hdl_toplevel="cic_fir_pipeline",
		hdl_toplevel_lang="vhdl",
		test_module="cic_fir_pipeline_tb",
		build_dir=BUILD_DIR,
		extra_env={
			"PYTHONPATH": os.pathsep.join(
				python_paths
			),
		},
		waves=waves_enabled,
	)


if __name__ == "__main__":
	test_cic_fir_pipeline_runner()