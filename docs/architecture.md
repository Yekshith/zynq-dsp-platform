# Zynq DSP Validation Platform — Architecture

## 1. Overview

This project implements a staged digital signal-processing pipeline for the Zynq-7000, beginning with a fixed-point CIC decimator and later extending to FIR compensation, RTL verification, streaming interfaces, and hardware execution on the ZedBoard.

This document freezes the CIC architecture, arithmetic behaviour, word widths, decimation timing, and model-to-RTL equivalence rules used for the `v0.1` implementation.

---

## 2. Signal Source Assumptions

The CIC input represents samples captured from an AD9226-class ADC interface.

| Property                  |            Frozen value |
| ------------------------- | ----------------------: |
| Sample width              |                 12 bits |
| Number format             | Signed two’s-complement |
| Nominal input sample rate |                 10 MSPS |
| Input range               |          -2048 to +2047 |

A 12-bit signed input is used because the AD9226 is a 12-bit ADC. A nominal rate of 10 MSPS provides a realistic initial hardware target while keeping the first FPGA integration and signal-integrity requirements manageable.

If the physical ADC module produces offset-binary data, conversion to signed two’s-complement must occur in the ADC capture interface before the sample enters the CIC. The CIC itself always receives signed samples.

---

## 3. CIC Parameter Selection

The first CIC decimator uses the following default parameters:

| Parameter          | Symbol | Value |
| ------------------ | -----: | ----: |
| Decimation factor  |      R |     8 |
| Number of stages   |      N |     3 |
| Differential delay |      M |     1 |

### Decimation factor: R = 8

The CIC produces one output sample for every eight input samples.

Output sample rate:

`f_out = f_in / R = 10 MSPS / 8 = 1.25 MSPS`

A power-of-two decimation factor simplifies the output counter and reduces the processing rate of the following FIR filter by a factor of eight.

### Number of stages: N = 3

Three cascaded integrator and comb stages provide substantially better attenuation around the CIC spectral nulls than a single-stage filter while keeping the architecture small enough to implement and verify clearly.

Increasing the number of stages improves rejection in the frequency bands that would fold into the decimated output, but it also increases passband droop and internal word growth. Three stages are selected as the initial compromise between alias rejection, hardware cost, and passband flatness.

The remaining passband droop will be corrected by the compensating FIR designed in Level 1.2.

### Differential delay: M = 1

A differential delay of one means each comb stage subtracts its previous low-rate input sample:

`y[k] = x[k] - x[k-1]`

This is the simplest and most common CIC configuration and requires only one delay register per comb stage.

---

## 4. Bit-Growth Derivation

The maximum DC gain of a CIC decimator is:

`G = (R × M)^N`

For the frozen parameters:

`G = (8 × 1)^3 = 512`

Since:

`512 = 2^9`

the CIC requires nine additional bits above the input width.

The full-precision CIC width is:

`B_CIC = B_in + ceil(N × log2(R × M))`

Substituting the frozen values:

`B_CIC = 12 + ceil(3 × log2(8 × 1))`

`B_CIC = 12 + 3 × 3`

`B_CIC = 21 bits`

The result can also be checked using the signed input limits.

Maximum positive result:

`2047 × 512 = 1,048,064`

Maximum negative result:

`-2048 × 512 = -1,048,576`

The range of a signed 21-bit value is:

`-2^20 to 2^20 - 1`

which equals:

`-1,048,576 to +1,048,575`

Therefore, both the maximum positive and maximum negative full-scale CIC outputs fit within 21 signed bits.

### Wrap-around arithmetic

All CIC additions and subtractions use signed two’s-complement modulo arithmetic.

The integrator states are permitted to wrap around the 21-bit range. This is not saturation and is not treated as an error. Because the integrators and combs use the same fixed-width modulo arithmetic, the later comb subtraction removes the accumulated history, including modulo wrap events.

This remains valid only when the selected width is large enough to represent the final CIC output range. For the frozen configuration of R = 8, N = 3, M = 1, and a 12-bit input, the derived 21-bit width satisfies this condition.

---

## 5. Word Widths

| Signal boundary               | Signed width |
| ----------------------------- | -----------: |
| CIC input                     |      12 bits |
| Integrator stage 1 state      |      21 bits |
| Integrator stage 2 state      |      21 bits |
| Integrator stage 3 state      |      21 bits |
| Decimated integrator value    |      21 bits |
| Comb stage 1 state and output |      21 bits |
| Comb stage 2 state and output |      21 bits |
| Comb stage 3 state and output |      21 bits |
| CIC output                    |      21 bits |

The 12-bit input is sign-extended to 21 bits before entering the first integrator.

Every integrator addition and every comb subtraction is explicitly wrapped to a signed 21-bit value.

The CIC output remains full-width. The CIC performs:

* no truncation;
* no rounding;
* no saturation;
* no normalization;
* no division by the CIC gain.

The Level 1.2 compensating FIR therefore inherits a signed 21-bit input. Its coefficient width, multiplier width, accumulator growth, rounding behaviour, and final output width must be derived starting from this 21-bit CIC output.

---

## 6. Decimation Mechanism

The CIC contains a decimation counter with values from `0` through `7`.

Every valid input sample is first processed by all three integrator stages.

When `counter == 7`:

1. The updated third-integrator value is passed into the comb section.
2. All three comb stages are evaluated.
3. One CIC output sample is produced.
4. The counter is reset to `0`.

Otherwise:

1. The counter is incremented by one.
2. The comb stages are not evaluated.
3. No output sample is produced.

The sequence is therefore:

```text
Input sample indices:  0  1  2  3  4  5  6  7 | 8  9  10  11  12  13  14  15
CIC output:                                  ↑                              ↑
```

The first CIC output is produced after processing input sample index `7`.

For an input sequence containing `L` samples, the expected number of output samples is:

`L_out = floor(L / R)`

For the frozen decimation factor:

`L_out = floor(L / 8)`

Incomplete groups containing fewer than eight samples do not produce an output.

---

## 7. Reset and Startup-Transient Contract

Reset places the CIC into a fully defined zero state.

Reset clears:

* every integrator state;
* every comb delay state;
* the decimation counter.

The first sample after reset is processed as input sample index `0`.

The startup transient caused by the zeroed integrator and comb states is part of the defined CIC response. It must appear identically in the Python model and the RTL implementation.

No startup outputs are discarded, hidden, or ignored during bit-exact comparison.

---

## 8. Model–RTL Equivalence Rules

The Python golden model created in Level 1.1 and the VHDL implementation created in Level 1.3 must obey the same arithmetic and timing contract.

### Fixed-width helper

The Python model will use the helper function:

```python
wrap_signed(value, width)
```

The function converts an integer into the equivalent signed two’s-complement value represented by exactly `width` bits.

For the default CIC, it will be called as:

```python
wrap_signed(value, 21)
```

after every integrator addition and every comb subtraction.

Before the helper is used inside the CIC model, it must have an isolated pytest unit test containing known:

* in-range cases;
* positive boundary cases;
* negative boundary cases;
* positive overflow cases;
* negative overflow cases.

### Processing order

Both implementations must use the following processing order for every input sample:

1. Validate that the input fits within the signed 12-bit range.
2. Sign-extend the input to the internal width.
3. Update integrator stage 1 and wrap the result to 21 bits.
4. Update integrator stage 2 using the current stage-1 result and wrap to 21 bits.
5. Update integrator stage 3 using the current stage-2 result and wrap to 21 bits.
6. Evaluate the decimation counter.
7. If `counter == 7`:

   * pass the current stage-3 result through comb stage 1;
   * pass the current comb-1 result through comb stage 2;
   * pass the current comb-2 result through comb stage 3;
   * wrap every subtraction to 21 bits;
   * produce one output sample;
   * reset the counter to `0`.
8. Otherwise:

   * increment the counter by one;
   * do not evaluate the comb stages;
   * produce no output.

The Python model and RTL must not introduce additional sample delays between integrator stages or between comb stages.

### Shared deterministic stimulus

Pytest and cocotb must use deterministic input sequences.

Impulse, step, sine, boundary-value, and later randomized stimuli must either be generated through shared helper functions or stored as shared test vectors.

If pseudo-random data is used, its seed must be fixed and documented.

The same input vector must produce exactly the same output vector in:

* the Python golden model;
* the VHDL RTL simulation.

The comparison tolerance is zero.

---

## 9. Parameterization

The CIC implementation must support the following parameters:

* decimation factor `R`;
* number of stages `N`;
* differential delay `M`;
* input width;
* internal width;
* output width.

The Python model will expose these through constructor arguments.

The VHDL implementation will expose the corresponding values through entity generics.

The following configuration is frozen as the default for project release `v0.1`:

```text
R              = 8
N              = 3
M              = 1
INPUT_WIDTH    = 12
INTERNAL_WIDTH = 21
OUTPUT_WIDTH   = 21
```

Changing these defaults requires recalculating:

* CIC gain;
* bit growth;
* internal width;
* output sample rate;
* output-count expectations;
* test reference values.
