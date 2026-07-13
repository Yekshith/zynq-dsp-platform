# Zynq DSP Validation Platform — Architecture

## 1. Overview

This project implements a staged digital signal-processing pipeline for the Zynq-7000, beginning with a fixed-point CIC decimator and later extending to FIR compensation, RTL verification, streaming interfaces, and hardware execution on the ZedBoard.

This document freezes the CIC and FIR architectures, arithmetic behaviour, word widths, timing rules, and model-to-RTL equivalence requirements used for the `v0.1` implementation.

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

---

## 10. FIR Compensation Filter v1

### 10.1 Purpose and Passband

The FIR compensation filter receives the signed 21-bit output of the CIC decimator at the reduced sample rate of 1.25 MSPS.

The FIR has two purposes:

1. compensate for the CIC passband droop over the selected useful signal band;
2. remove the CIC DC gain of 512 so that the output amplitude returns approximately to the original ADC sample scale.

The desired combined response is:

```text
AD9226-style input
        ↓
CIC decimator: gain of 512 with passband droop
        ↓
FIR compensation: inverse droop and gain normalization
        ↓
approximately flat, normalized output
```

Within the useful passband, the FIR response should approximately satisfy:

`H_FIR(f) ≈ 1 / H_CIC(f)`

At DC, the CIC gain is 512. Therefore, the FIR coefficient sum should be approximately:

`sum(coefficients) ≈ 1 / 512`

The frozen FIR passband is:

`0 Hz to 200 kHz`

The FIR input sample rate is:

`f_FIR = 10 MSPS / 8 = 1.25 MSPS`

The corresponding output Nyquist frequency is:

`f_Nyquist = 1.25 MSPS / 2 = 625 kHz`

The 200 kHz passband remains well below the 625 kHz Nyquist limit and avoids attempting to compensate the CIC close to its heavily attenuated spectral edge.

The initial design target for the combined CIC-to-FIR response is:

`passband ripple within ±0.25 dB from 0 Hz to 200 kHz`

This value is a design target. It must be measured after the floating-point coefficients are designed and measured again after coefficient quantization.

The FIR cannot recover spectral content that has already aliased during CIC decimation. Its role is passband correction and gain normalization, not reconstruction of aliased frequencies.

---

### 10.2 FIR Structure and Tap Count

The compensation filter uses a direct-form, linear-phase FIR structure with 31 taps.

The frozen tap count is:

`TAPS = 31`

An odd tap count permits a symmetric Type-I linear-phase impulse response.

For 31 taps, the group delay is:

`GROUP_DELAY = (TAPS - 1) / 2`

`GROUP_DELAY = (31 - 1) / 2 = 15 output samples`

At the 1.25 MSPS FIR sample rate, the time delay is:

`15 / 1,250,000 = 12 microseconds`

The floating-point and quantized coefficient sets must remain symmetric:

`h[k] = h[TAPS - 1 - k]`

Coefficient symmetry may later be used to reduce the number of hardware multiplications. The Level 1.2 Python golden model will initially evaluate every tap explicitly so that the arithmetic and processing order remain clear.

Thirty-one taps are selected as the initial compromise between:

* CIC droop compensation accuracy;
* hardware multiplier and accumulator cost;
* implementation simplicity;
* deterministic group delay.

The tap count must not be changed after coefficient generation without repeating the frequency-response, width, and fixed-point error analysis.

---

### 10.3 Coefficient Representation

The FIR coefficients use signed fixed-point integers with:

```text
COEFFICIENT_WIDTH = 18 bits
FRACTIONAL_BITS   = 17 bits
COEFFICIENT_SCALE = 2^17 = 131072
```

A stored coefficient integer represents the real value:

`coefficient_real = coefficient_integer / 2^17`

Floating-point coefficients are quantized using:

`coefficient_integer = round(coefficient_float × 2^17)`

The representable signed 18-bit integer range is:

`-131072 to +131071`

After applying the fractional scaling, the represented real-value range is approximately:

`-1.0 to +0.999992`

Example:

```text
floating-point coefficient = 0.125
stored coefficient         = round(0.125 × 131072)
stored coefficient         = 16384
represented value          = 16384 / 131072
represented value          = 0.125
```

The coefficients include both:

* the inverse CIC passband shape over 0 Hz to 200 kHz;
* the CIC gain normalization factor of approximately `1 / 512`.

No separate division by 512 occurs after the FIR.

The quantized coefficient set must be checked for:

* exact tap count;
* signed 18-bit range compliance;
* symmetry;
* coefficient sum;
* floating-point versus quantized frequency-response error.

---

### 10.4 Product and Accumulator Widths

The FIR input is a signed 21-bit integer with no fractional bits.

Each coefficient is a signed 18-bit integer representing a value with 17 fractional bits.

The full signed multiplication width is:

`PRODUCT_WIDTH = INPUT_WIDTH + COEFFICIENT_WIDTH`

`PRODUCT_WIDTH = 21 + 18 = 39 bits`

Each product therefore has:

* a signed width of 39 bits;
* 17 fractional bits inherited from the coefficient representation.

The product scaling is:

`product_real = product_integer / 2^17`

Products are accumulated without first removing the 17 fractional bits. Rounding or shifting each product separately would introduce unnecessary quantization error.

The required conservative accumulator growth for 31 products is:

`ACCUMULATOR_WIDTH = PRODUCT_WIDTH + ceil(log2(TAPS))`

Substituting the frozen values:

`ACCUMULATOR_WIDTH = 39 + ceil(log2(31))`

`ACCUMULATOR_WIDTH = 39 + 5`

`ACCUMULATOR_WIDTH = 44 bits`

The frozen arithmetic widths are therefore:

| Signal boundary       |              Signed width | Fractional bits |
| --------------------- | ------------------------: | --------------: |
| FIR input             |                   21 bits |               0 |
| FIR coefficient       |                   18 bits |              17 |
| Multiplier output     |                   39 bits |              17 |
| FIR accumulator       |                   44 bits |              17 |
| Scaled integer result | 44 bits before saturation |               0 |
| FIR output            |                   16 bits |               0 |

The Python model must explicitly wrap each multiplier result to 39 signed bits and each accumulator addition to 44 signed bits so that its behaviour can later be reproduced exactly in RTL.

No coefficient cancellation is assumed when selecting the accumulator width. The five guard bits cover the conservative accumulation of 31 full-width products.

---

### 10.5 Rounding and Scaling

After all 31 products have been accumulated, the 44-bit accumulator still contains 17 fractional bits.

Scaling back to an integer sample requires division by:

`2^17 = 131072`

The division is implemented as a signed arithmetic right shift by 17 bits after rounding.

The frozen rounding policy is:

`round to nearest, with exact half-way cases rounded away from zero`

Rounding occurs once, after the complete accumulation.

For a non-negative accumulator:

```text
rounded = (accumulator + 2^16) >> 17
```

For a negative accumulator:

```text
rounded = -(((-accumulator) + 2^16) >> 17)
```

Examples:

```text
+1.4 → +1
+1.5 → +2
-1.4 → -1
-1.5 → -2
```

The FIR must not:

* truncate every product separately;
* round every product separately;
* shift before completing the accumulation.

The required order is:

```text
multiply all taps
        ↓
accumulate full-width products
        ↓
round once
        ↓
shift right by 17 bits
        ↓
saturate to the output width
```

The Python model and future RTL must use the same rounding rule. A difference in negative-number rounding is considered a bit-exact mismatch.

---

### 10.6 Output Width and Saturation

The FIR produces a signed 16-bit integer output.

The frozen output width is:

`OUTPUT_WIDTH = 16 bits`

The signed output range is:

`-32768 to +32767`

The original ADC source is 12 bits. After the FIR removes the CIC gain, a nominal in-band signal should return close to its original ADC amplitude.

The 16-bit result provides four additional bits above the original ADC width for:

* compensation gain near the passband edge;
* coefficient-quantization error;
* startup transient headroom;
* later processing and software transport.

After rounding and removing the 17 fractional bits, the result is saturated to the signed 16-bit range.

The saturation rule is:

```text
result > +32767  → +32767
result < -32768  → -32768
otherwise        → result unchanged
```

The FIR output must not use wrap-around arithmetic.

Internal products and accumulator values use their frozen full widths. Saturation occurs only once, at the final FIR output boundary.

The complete numeric path is:

```text
21-bit signed CIC output
        ↓
18-bit signed coefficient with 17 fractional bits
        ↓
39-bit signed product with 17 fractional bits
        ↓
44-bit signed accumulator with 17 fractional bits
        ↓
round to nearest, ties away from zero
        ↓
arithmetic scaling by 2^17
        ↓
saturate
        ↓
16-bit signed FIR output
```

---

### 10.7 Frozen FIR Defaults

The following values are frozen as the default FIR configuration for project release `v0.1`:

```text
TAPS                = 31
INPUT_RATE          = 1.25 MSPS
PASSBAND_START      = 0 Hz
PASSBAND_EDGE       = 200 kHz
PASSBAND_TARGET     = ±0.25 dB
INPUT_WIDTH         = 21 bits
COEFFICIENT_WIDTH   = 18 bits
FRACTIONAL_BITS     = 17 bits
PRODUCT_WIDTH       = 39 bits
ACCUMULATOR_WIDTH   = 44 bits
OUTPUT_WIDTH        = 16 bits
ROUNDING            = nearest, ties away from zero
OUTPUT_OVERFLOW     = saturation
CIC_NORMALIZATION   = included in coefficients
FIR_STRUCTURE       = direct-form linear-phase
GROUP_DELAY         = 15 output samples
```

The coefficient values are not frozen in this section. They will be designed, quantized, measured, and committed during the next Level 1.2 task.

Changing any frozen FIR default requires repeating the relevant:

* coefficient design;
* coefficient quantization;
* frequency-response analysis;
* multiplier and accumulator width analysis;
* fixed-point versus floating-point comparison;
* CIC-to-FIR chain tests.
