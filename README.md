# Zynq DSP Validation Platform

[![CI](https://github.com/Yekshith/zynq-dsp-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Yekshith/zynq-dsp-platform/actions/workflows/ci.yml)

A bit-exact, fixed-point DSP pipeline developed for FPGA implementation and verification on the Zynq-7000 platform.

The current Level 1 design accepts signed 12-bit ADC samples at 10 MSPS, performs multiplier-free decimation using a three-stage CIC filter, corrects the CIC passband droop with a 31-tap fixed-point FIR filter, and produces signed 16-bit output samples at 1.25 MSPS.

The complete signal-processing chain is implemented as:

* bit-exact Python golden models;
* synthesizable VHDL RTL;
* cocotb model-to-RTL regressions;
* GHDL simulation;
* Dockerized development and CI tooling;
* GitHub Actions automation.

---

## Current Status

### Level 1: CIC–FIR DSP Pipeline

**Level 1 released as `v0.1`. GitHub Actions verification is passing.**

| Component                            |           Status |
| ------------------------------------ | ---------------: |
| Architecture and arithmetic contract |         Complete |
| Deterministic stimulus generation    |         Complete |
| CIC Python golden model              |         Complete |
| FIR coefficient-design flow          |         Complete |
| Fixed-point FIR Python model         |         Complete |
| Complete Python pipeline model       |         Complete |
| CIC VHDL RTL                         |         Complete |
| FIR VHDL RTL                         |         Complete |
| Structural CIC–FIR top level         |         Complete |
| CIC cocotb regression                |          Passing |
| FIR cocotb regression                |          Passing |
| Pipeline cocotb regression           |          Passing |
| Docker simulation environment        |         Complete |
| GitHub Actions workflow              | Passing on `main` |
| ZedBoard hardware integration        |     Future level |
| ADC capture, AXI and DMA integration |     Future level |

Level 1 is released through the annotated `v0.1` tag.

Requirements traceability: [`docs/requirements.md`](docs/requirements.md).

---

## Project Objective

The project demonstrates a complete FPGA-oriented DSP development workflow:

```text
requirements
    ↓
fixed-point architecture
    ↓
Python golden models
    ↓
VHDL RTL
    ↓
model-to-RTL verification
    ↓
Dockerized continuous integration
    ↓
future Zynq hardware integration
```

The focus is not only on creating a working filter. The design explicitly defines and verifies:

* signed word widths;
* overflow behaviour;
* rounding behaviour;
* saturation behaviour;
* valid-sample timing;
* reset behaviour;
* decimation phase;
* pipeline latency;
* frequency-response requirements;
* bit-exact Python-to-VHDL equivalence.

---

## Level 1 Architecture

```text
12-bit signed ADC-style input
10 MSPS
        │
        ▼
┌───────────────────────────┐
│ Three-stage CIC decimator │
│ R = 8, N = 3, M = 1       │
│ 21-bit modulo arithmetic  │
└───────────────────────────┘
        │
        │ 21-bit signed samples
        │ 1.25 MSPS
        ▼
┌───────────────────────────┐
│ 31-tap FIR compensation   │
│ Signed Q17 coefficients   │
│ 44-bit accumulator        │
└───────────────────────────┘
        │
        ▼
16-bit signed output
1.25 MSPS
```

### Signal contract

| Property                  |                Value |
| ------------------------- | -------------------: |
| Input width               |        12-bit signed |
| Input range               |   `-2048` to `+2047` |
| Input sample rate         |              10 MSPS |
| CIC decimation factor     |                    8 |
| CIC stages                |                    3 |
| CIC differential delay    |                    1 |
| CIC internal/output width |              21 bits |
| CIC output sample rate    |            1.25 MSPS |
| FIR tap count             |                   31 |
| FIR coefficient format    |           Signed Q17 |
| FIR product width         |              39 bits |
| FIR accumulator width     |              44 bits |
| Final output width        |        16-bit signed |
| Final output range        | `-32768` to `+32767` |

For the full arithmetic and timing contract, see [`docs/architecture.md`](docs/architecture.md).

---

## Why CIC Followed by FIR?

The CIC filter performs sample-rate reduction using only:

* adders;
* subtractors;
* registers;
* a decimation counter.

It does not require multipliers, making it efficient at the 10 MSPS input rate.

The CIC also introduces:

* a DC gain of 512;
* passband droop;
* a non-flat useful-band response.

The following FIR filter therefore performs three jobs:

1. corrects the CIC passband droop;
2. normalizes the CIC gain;
3. attenuates unwanted high-frequency content.

The FIR runs after decimation at 1.25 MSPS, reducing its processing workload by a factor of eight compared with operating at the original input rate.

---

## CIC Decimator

The CIC uses:

```text
R = 8  decimation factor
N = 3  integrator and comb stages
M = 1  differential delay
```

Its maximum DC gain is:

```text
(R × M)^N = (8 × 1)^3 = 512
```

The 12-bit input therefore requires nine additional bits:

```text
12 input bits + 9 growth bits = 21 bits
```

The CIC contains:

```text
input
  ↓
integrator 1
  ↓
integrator 2
  ↓
integrator 3
  ↓
keep one result after every eight accepted samples
  ↓
comb 1
  ↓
comb 2
  ↓
comb 3
  ↓
output
```

### Overflow policy

All CIC additions and subtractions use signed 21-bit two's-complement wrapping.

Saturation is deliberately not used inside the CIC. CIC operation relies on consistent modulo arithmetic across its integrator and comb stages.

### Output phase

One output is produced after every eight accepted input samples.

Using zero-based input indexing:

```text
7, 15, 23, 31, ...
```

Only samples accepted while `in_valid` is asserted advance the filter state and decimation counter.

---

## FIR Compensation Filter

The FIR is a 31-tap symmetric linear-phase filter.

Its responsibilities are:

* inverse CIC-droop compensation;
* gain normalization;
* stopband filtering;
* final conversion to signed 16-bit output.

### Frequency specification

| Region                   |                Requirement |
| ------------------------ | -------------------------: |
| Passband                 |                  0–200 kHz |
| Transition band          |                200–350 kHz |
| Stopband begins          |                    350 kHz |
| Output Nyquist frequency |                    625 kHz |
| Passband target          |            Within ±0.25 dB |
| Stopband target          | At least 40 dB attenuation |

### Quantized response

The final signed-Q17 coefficients achieve:

| Metric                   | Quantized result |     Requirement | Status |
| ------------------------ | ---------------: | --------------: | -----: |
| Combined passband ripple |         0.188 dB | Within ±0.25 dB |   Pass |
| Maximum stopband level   |        -45.02 dB |        ≤ -40 dB |   Pass |
| Combined DC gain         |       1.00390625 | Approximately 1 |   Pass |

The floating-point coefficients are not treated as the final result. The frequency response is measured again after Q17 coefficient quantization because the FPGA uses the quantized integer coefficients.

See [`docs/fir_design.md`](docs/fir_design.md) for the complete FIR design record.

---

## Frozen FIR Coefficients

The signed Q17 integer coefficients are:

```text
[
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
     0
]
```

The coefficients are stored in both:

```text
model/fir_coefficients.py
rtl/fir_coefficients_pkg.vhd
```

The Python and VHDL implementations must use identical values.

---

## Fixed-Point Arithmetic

### CIC arithmetic

```text
12-bit input
    ↓
sign extension to 21 bits
    ↓
21-bit wrapped integrator arithmetic
    ↓
21-bit wrapped comb arithmetic
    ↓
21-bit CIC output
```

### FIR arithmetic

```text
21-bit sample × 18-bit Q17 coefficient
                ↓
          39-bit product
                ↓
      44-bit wide accumulation
                ↓
       round once after summing
                ↓
        shift right by 17 bits
                ↓
       saturate to signed 16-bit
```

Rounding occurs once after the complete multiply-accumulate operation.

The final output saturates to:

```text
-32768 to +32767
```

Saturating only at the final output avoids corrupting the FIR transfer function through repeated intermediate clipping.

---

## Timing and Reset Behaviour

### Valid handling

When `in_valid = 1`:

* the input sample is accepted;
* CIC state advances;
* the decimation counter advances;
* an output may be produced.

When `in_valid = 0`:

* the input is ignored;
* CIC and FIR state are preserved;
* the decimation counter is preserved;
* no new output is generated.

### Reset

Reset is synchronous.

Reset clears:

* CIC integrator states;
* CIC comb-delay states;
* CIC decimation counter;
* FIR sample history;
* output samples;
* output-valid state.

The startup response after reset is deterministic and is included in model-to-RTL verification.

### Pipeline latency

The CIC registers a low-rate result. The FIR observes that registered result on the following rising edge.

The RTL therefore adds one clock of interface latency between CIC output generation and FIR processing.

This changes timing but does not change:

* output values;
* output count;
* output sample rate.

---

## Verification Strategy

The project uses a layered verification approach.

```text
Python unit tests
    ↓
individual block models
    ↓
complete Python pipeline
    ↓
individual RTL regressions
    ↓
complete RTL pipeline regression
```

### Golden-model verification

The Python models explicitly reproduce the hardware rules:

* signed input limits;
* fixed register widths;
* two's-complement wrapping;
* Q17 coefficient scaling;
* wide accumulation;
* ties-away-from-zero rounding;
* final saturation;
* reset and valid timing;
* decimation phase.

The comparison requirement is zero tolerance:

```python
assert actual == expected
```

Every VHDL output sample must match the Python golden model exactly.

---

## Verification Results

### Python regression

```text
47 tests passed
```

The Python tests cover:

* signed wrapping;
* input-range checking;
* initial and reset state;
* CIC integrator progression;
* decimation phase;
* output count;
* impulse response;
* step response;
* positive full-scale input;
* negative full-scale input;
* internal wrap events;
* sine-wave frequency preservation;
* FIR coefficient count and symmetry;
* FIR rounding;
* FIR saturation;
* FIR impulse response;
* FIR group delay;
* gain normalization;
* complete pipeline composition;
* floating-point frequency response;
* quantized frequency response;
* coefficient regeneration.

### RTL regressions

| Regression                     | Toolchain        | Result |
| ------------------------------ | ---------------- | -----: |
| CIC model vs RTL               | cocotb + GHDL    |   Pass |
| FIR model vs RTL               | cocotb + GHDL    |   Pass |
| Complete pipeline model vs RTL | cocotb + GHDL    |   Pass |
| Model-to-RTL mismatches        | Exact comparison |      0 |

Observed complete-pipeline result:

```text
TESTS=1 PASS=1 FAIL=0
SIM TIME=150365 ns
```

---

## Repository Structure

```text
zynq-dsp-platform/
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── ci/
│   └── Dockerfile
│
├── docs/
│   ├── architecture.md
│   ├── fir_design.md
│   ├── requirements.md
│   └── timing_closure.md
│
├── fpga/
│   ├── bd/
│   ├── tcl/
│   └── xdc/
│
├── model/
│   ├── cic.py
│   ├── fir.py
│   ├── fir_coefficients.py
│   ├── pipeline.py
│   ├── stimulus.py
│   ├── test_cic.py
│   ├── test_fir.py
│   ├── test_fir_response.py
│   └── test_pipeline.py
│
├── rtl/
│   ├── cic_decimator.vhd
│   ├── cic_fir_pipeline.vhd
│   ├── fir_coefficients_pkg.vhd
│   └── fir_comp.vhd
│
├── scripts/
│   └── design_fir.py
│
├── sw/
│   ├── app_freertos/
│   └── driver/
│
├── tb/
│   ├── cocotb/
│   │   ├── cic_decimator_tb.py
│   │   ├── cic_fir_pipeline_tb.py
│   │   ├── fir_comp_tb.py
│   │   ├── test_cic_runner.py
│   │   ├── test_fir_runner.py
│   │   └── test_pipeline_runner.py
│   ├── sva/
│   └── vunit/
│
└── README.md
```

Some directories are placeholders for later project levels.

---

## Tools

The Level 1 workflow uses:

| Area                       | Tool                 |
| -------------------------- | -------------------- |
| Golden models              | Python               |
| Numerical processing       | NumPy and SciPy      |
| Model tests                | pytest               |
| RTL language               | VHDL                 |
| RTL simulator              | GHDL                 |
| Model-to-RTL verification  | cocotb               |
| Reproducible environment   | Docker               |
| Continuous integration     | GitHub Actions       |
| Future FPGA implementation | AMD Vivado           |
| Target platform            | ZedBoard / Zynq-7000 |

---

## Running the Regressions

### Prerequisite

Install Docker and clone the repository:

```bash
git clone https://github.com/Yekshith/zynq-dsp-platform.git
cd zynq-dsp-platform
```

### Build the CI image

```bash
docker build --no-cache -t zynq-ci ci/
```

### Run all Python model tests

```bash
docker run --rm -v "$PWD:/work" zynq-ci \
	pytest model/ -v
```

### Run the CIC RTL regression

Remove the previous simulation build if required:

```bash
sudo rm -rf sim_build/cic_decimator
```

Run the test:

```bash
docker run --rm -v "$PWD:/work" zynq-ci \
	pytest tb/cocotb/test_cic_runner.py -v -s
```

### Run the FIR RTL regression

```bash
sudo rm -rf sim_build/fir_comp

docker run --rm -v "$PWD:/work" zynq-ci \
	pytest tb/cocotb/test_fir_runner.py -v -s
```

### Run the complete pipeline regression

```bash
sudo rm -rf sim_build/cic_fir_pipeline

docker run --rm -v "$PWD:/work" zynq-ci \
	pytest tb/cocotb/test_pipeline_runner.py -v -s
```

The cocotb experimental-runner warning does not indicate a test failure.

---

## Reproducing the FIR Coefficients

The coefficient-design script:

```text
scripts/design_fir.py
```

performs the following process:

```text
calculate the CIC response
    ↓
define the inverse-droop FIR target
    ↓
design the floating-point filter
    ↓
quantize the coefficients to Q17
    ↓
measure the combined CIC–FIR response
    ↓
reject the design if requirements are not met
```

Run the related regression using:

```bash
docker run --rm -v "$PWD:/work" zynq-ci \
	pytest model/test_fir_response.py -v
```

This verifies that the committed coefficients can be regenerated and still meet the frozen response requirements.

---

## CI

GitHub Actions uses the same Docker-based environment as local development.

This reduces differences between:

* the developer machine;
* the simulator environment;
* the CI runner.

The intended CI regression includes:

```text
Python model tests
CIC cocotb regression
FIR cocotb regression
complete pipeline cocotb regression
```

The workflow runs on pushes and pull requests.

---

## Key Engineering Decisions

### Multirate architecture

The multiplier-free CIC performs high-rate decimation. The multiplier-based FIR operates only after the sample rate has been reduced.

### Explicit arithmetic policies

The design does not rely on vague “fixed-point” behaviour. Wrapping, rounding and saturation are defined at specific boundaries.

### Bit-exact golden models

The Python models reproduce hardware arithmetic rather than using floating-point approximations.

### Zero-tolerance comparison

RTL output must match the golden model exactly. Numerical tolerances are not used to hide implementation differences.

### Deterministic stimulus

Impulse, step, sine and boundary-value sequences are shared and reproducible.

### Separate unit and integration tests

The CIC and FIR are tested individually before the complete pipeline is tested. This makes failures easier to isolate.

### Reproducible tooling

Docker provides the same GHDL, Python and cocotb environment locally and in CI.

---

## Debugging Lessons

### Cocotb could not locate `libpython`

The container required the Python development packages and an explicit `LIBPYTHON_LOC` path.

### GHDL elaboration and execution directories differed

The cocotb runners initially elaborated the design inside the build directory but attempted to run it elsewhere. Removing the incorrect `test_dir` setting fixed the problem.

### Cocotb write attempted during a read-only phase

One test vector ended in `ReadOnly()`, and the following reset attempted to write immediately. Waiting for a writable clock phase before driving the next vector fixed the scheduler error.

These issues and their fixes are part of the project’s reproducibility and verification record.

---

## Current Scope

Level 1 proves the fixed-point DSP core in simulation.

It does not yet include:

* physical ADC capture;
* clock-domain crossing;
* asynchronous FIFO integration;
* AXI-Stream interfaces;
* AXI DMA;
* processing-system software;
* DDR buffering;
* UDP streaming;
* ILA hardware captures;
* synthesis and timing-closure evidence.

Those items belong to later project levels and should not be interpreted as completed features.

---

## Roadmap

### Level 1 — Fixed-point DSP core

* CIC golden model;
* compensation FIR;
* VHDL RTL;
* bit-exact cocotb verification;
* Docker and CI.

### Level 2 — Streaming interfaces

* ready/valid stream contract;
* backpressure handling;
* framing;
* protocol assertions;
* randomized stalls.

### Level 3 — Zynq integration

* ADC capture;
* clock-domain crossing;
* asynchronous FIFO;
* AXI-Stream integration;
* AXI DMA;
* register map.

### Level 4 — Hardware demonstration

* ZedBoard execution;
* ILA evidence;
* captured sample frames;
* PS software;
* host-side visualization.

### Level 5 — Engineering closure

* synthesis reports;
* resource utilization;
* timing analysis;
* deliberate timing-closure exercise;
* performance and design trade-off documentation.

---

## Portfolio Value

This project demonstrates practical experience in:

* DSP architecture;
* multirate filtering;
* fixed-point arithmetic;
* Python modelling;
* synthesizable VHDL;
* model-based verification;
* cocotb testbench development;
* simulator debugging;
* regression automation;
* Docker;
* GitHub Actions;
* verification-driven FPGA development.

The main result is not merely a working CIC or FIR filter. It is a reproducible workflow that connects an explicit numerical contract to a bit-exact model, an RTL implementation and automated verification.

---

## Author

**Yekshith Bushan**

GitHub: [@Yekshith](https://github.com/Yekshith)

---

## Release Target

```text
v0.1 — Verified fixed-point CIC–FIR pipeline
```

Current state: the Level 1 implementation, documentation, branch push, GitHub Actions regression, and annotated `v0.1` tag are complete.

The release is complete only after:

* all Level 1 files are committed;
* the branch is pushed;
* GitHub Actions passes;
* the `v0.1` annotated tag is created and pushed.
