# Requirements Traceability Matrix

## 1. Purpose

This document maps each system requirement to its implementation, verification evidence, and current completion status.

The project is developed incrementally. Requirements that belong to later phases remain explicitly marked as **Planned** rather than being presented as completed.

---

## 2. Status Definitions

| Status          | Meaning                                                               |
| --------------- | --------------------------------------------------------------------- |
| **Verified**    | Implemented and supported by automated tests or captured evidence     |
| **Implemented** | Design exists, but final required verification evidence is incomplete |
| **Planned**     | Assigned to a later project phase                                     |
| **Deferred**    | Intentionally postponed with a documented reason                      |

---

## 3. Requirements Matrix

| ID      | Requirement                                                                                                                                                           | Implementation                                                                                                               | Verification evidence                                                                                                                                                                                                                                                                                                                                      | Status                                           |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| **R1**  | The platform shall capture signed 12-bit samples at a sample rate of no more than 10 MSPS from the AD9226 interface or an internal test-pattern source.               | Planned `adc_capture` and `test_pattern_src` RTL modules                                                                     | Future cocotb tests and ZedBoard hardware capture                                                                                                                                                                                                                                                                                                          | **Planned — Phase 3**                            |
| **R2**  | The capture clock domain shall be asynchronous to the processing clock domain, with data crossing through a dual-clock FIFO using Gray-coded pointers.                | Planned `rtl/async_fifo.vhd` and domain-specific reset synchronizers                                                         | Future randomized CDC/FIFO regression and CDC documentation                                                                                                                                                                                                                                                                                                | **Planned — Phase 2**                            |
| **R3**  | The asynchronous FIFO shall not overflow silently or underflow. Overflow shall be reported through a sticky status flag.                                              | Planned FIFO full/empty protection and overflow-sticky output                                                                | Future cocotb randomized regression and SystemVerilog assertions                                                                                                                                                                                                                                                                                           | **Planned — Phase 2**                            |
| **R4**  | For identical accepted input samples, the CIC and FIR output shall be bit-exact against the Python golden model.                                                      | `model/cic.py`, `model/fir.py`, `model/pipeline.py`, `rtl/cic_decimator.vhd`, `rtl/fir_comp.vhd`, `rtl/cic_fir_pipeline.vhd` | [`model/test_cic.py`](../model/test_cic.py), [`model/test_fir.py`](../model/test_fir.py), [`model/test_pipeline.py`](../model/test_pipeline.py), [`tb/cocotb/cic_decimator_tb.py`](../tb/cocotb/cic_decimator_tb.py), [`tb/cocotb/fir_comp_tb.py`](../tb/cocotb/fir_comp_tb.py), [`tb/cocotb/cic_fir_pipeline_tb.py`](../tb/cocotb/cic_fir_pipeline_tb.py) | **Verified — Level 1**                           |
| **R5**  | Two AXI-Stream sources shall share one DMA output channel through a custom priority arbiter.                                                                          | Planned `rtl/stream_arbiter.vhd`                                                                                             | Future cocotb and SystemVerilog assertion regressions                                                                                                                                                                                                                                                                                                      | **Planned — Phase 2**                            |
| **R6**  | Arbiter grants shall be one-hot or idle, and starvation of the low-priority source shall be bounded.                                                                  | Planned configurable starvation counter in `stream_arbiter`                                                                  | Future `$onehot0` and bounded-starvation assertions                                                                                                                                                                                                                                                                                                        | **Planned — Phase 2**                            |
| **R7**  | No AXI-Stream beat shall be lost or duplicated under downstream backpressure.                                                                                         | Planned ready/valid handling in the arbiter and integration path                                                             | Future randomized backpressure regression, assertions, and ILA capture                                                                                                                                                                                                                                                                                     | **Planned — Phases 2–3**                         |
| **R8**  | Runtime configuration shall be exposed through an AXI4-Lite register map using the frozen register specification.                                                     | Planned `rtl/axil_regmap.vhd`                                                                                                | Future cocotb read/write regression and protocol assertions                                                                                                                                                                                                                                                                                                | **Planned — Phase 2**                            |
| **R9**  | Processed frames shall be written into PS DDR using AXI DMA, and the software driver shall expose init, configure, start, stop, interrupt, and frame-read operations. | Planned Vivado AXI DMA integration and `sw/driver/` implementation                                                           | Future on-target DDR frame test and ILA evidence                                                                                                                                                                                                                                                                                                           | **Planned — Phase 3**                            |
| **R10** | Processing-system control shall run as a FreeRTOS task.                                                                                                               | Planned Vitis FreeRTOS application in `sw/app_freertos/`                                                                     | Future on-target execution procedure                                                                                                                                                                                                                                                                                                                       | **Planned — Phase 3**                            |
| **R11** | Processed frames shall be transmitted over UDP and displayed by a host application at no less than 5 frames per second.                                               | Planned lwIP telemetry and Python host plot                                                                                  | Future network test and recorded demonstration                                                                                                                                                                                                                                                                                                             | **Planned — Phase 4**                            |
| **R12** | The processing clock domain shall meet timing at 100 MHz, with the timing-closure history documented.                                                                 | Planned Vivado constraints and implementation work                                                                           | Future timing reports and [`docs/timing_closure.md`](timing_closure.md) before/after WNS evidence                                                                                                                                                                                                                                                          | **Planned — Phase 3**                            |
| **R13** | The complete cocotb regression shall run inside Docker CI on every push and pull request. | [`ci/Dockerfile`](../ci/Dockerfile) and [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | [GitHub Actions run 29352726295](https://github.com/Yekshith/zynq-dsp-platform/actions/runs/29352726295) completed successfully for commit `8beb950`; the workflow ran the Python model tests plus CIC, FIR, and complete-pipeline cocotb regressions | **Verified — Level 1** |
| **R14** | Every system requirement shall trace to at least one automated test or captured engineering artifact.                                                                 | This traceability matrix and linked implementation/evidence files                                                            | Review of this document at every release milestone                                                                                                                                                                                                                                                                                                         | **Implemented — grows each phase**               |

---

## 4. Level 1 Verification Evidence

### Python golden-model regression

The Level 1 Python regression verifies:

* signed two's-complement wrapping;
* CIC state initialization;
* CIC decimation phase and output count;
* impulse, step, sine, and full-scale behaviour;
* FIR coefficient count and symmetry;
* FIR fixed-point rounding and saturation;
* FIR impulse response and group delay;
* complete CIC-to-FIR model composition;
* floating-point and quantized frequency-response requirements.

Expected Level 1 result:

```text
47 tests passed
```

### RTL regression

The RTL regressions compare VHDL output against the Python golden models with zero tolerance.

| Regression                         | Runner                                                                      |
| ---------------------------------- | --------------------------------------------------------------------------- |
| CIC model versus RTL               | [`tb/cocotb/test_cic_runner.py`](../tb/cocotb/test_cic_runner.py)           |
| FIR model versus RTL               | [`tb/cocotb/test_fir_runner.py`](../tb/cocotb/test_fir_runner.py)           |
| Complete pipeline model versus RTL | [`tb/cocotb/test_pipeline_runner.py`](../tb/cocotb/test_pipeline_runner.py) |

Comparison rule:

```python
assert actual == expected
```

Expected model-to-RTL mismatch count:

```text
0
```

---

## 5. Release-Gate Rules

A requirement may be marked **Verified** only when:

1. the implementation exists;
2. the required test or artifact exists;
3. the evidence is accessible from this repository;
4. the relevant regression or validation procedure passes.

A future requirement must remain **Planned** until these conditions are met.

At each release:

* `v0.1` updates Level 1 DSP and CI evidence;
* `v0.2` updates FIFO, arbiter, register-map, SVA, and VUnit evidence;
* `v0.3` updates ZedBoard, DMA, driver, FreeRTOS, ILA, and timing evidence;
* `v0.4` updates UDP, host-visualization, and final demonstration evidence.

---

## 6. Current Release Summary

| Release | Scope                                                                     | Current state                                        |
| ------- | ------------------------------------------------------------------------- | ---------------------------------------------------- |
| `v0.1`  | Bit-exact fixed-point CIC–FIR pipeline                                    | **Released and verified**                          |
| `v0.2`  | Async FIFO, priority arbiter, AXI-Lite regmap, SVA and VUnit              | Planned                                              |
| `v0.3`  | ZedBoard integration, AXI DMA, C driver, FreeRTOS, ILA and timing closure | Planned                                              |
| `v0.4`  | UDP telemetry, host plot and final demonstration                          | Planned                                              |
