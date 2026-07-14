# FIR Compensation Filter Design

## 1. Purpose

The FIR compensation filter follows the CIC decimator and performs:

* CIC passband-droop compensation;
* CIC gain normalization;
* conversion from a signed 21-bit CIC result to a signed 16-bit output.

The processing chain is:

```text
12-bit ADC samples at 10 MSPS
        ↓
3-stage CIC decimator, R = 8
        ↓
21-bit samples at 1.25 MSPS
        ↓
31-tap FIR compensation filter
        ↓
16-bit compensated samples at 1.25 MSPS
```

---

## 2. Frozen FIR Contract

```text
TAPS                = 31
INPUT_RATE          = 1.25 MSPS
PASSBAND_START      = 0 Hz
PASSBAND_EDGE       = 200 kHz
STOPBAND_START      = 350 kHz
PASSBAND_TARGET     = ±0.25 dB
STOPBAND_TARGET     = at most -40 dB

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

---

## 3. CIC Response Used for Compensation

The unnormalized CIC magnitude response is:

```text
                    sin(π f R M / Fs)
|H_CIC(f)| = | -------------------------- |^N
                    sin(π f / Fs)
```

For the frozen CIC configuration:

```text
R  = 8
N  = 3
M  = 1
Fs = 10 MSPS
```

The DC gain is:

```text
H_CIC(0) = (R × M)^N
         = 8^3
         = 512
```

Selected CIC response values are:

| Frequency | CIC magnitude |     Normalized response |
| --------: | ------------: | ----------------------: |
|      0 Hz |    512.000000 |             0.000000 dB |
|   100 kHz |    496.294064 | approximately -0.271 dB |
|   200 kHz |    451.640498 | approximately -1.090 dB |

The FIR target inside the passband is approximately:

```text
H_FIR(f) = 1 / H_CIC(f)
```

The FIR coefficient sum should therefore be close to:

```text
1 / 512 = 0.001953125
```

---

## 4. Floating-Point Design Method

The filter is designed using `scipy.signal.firls`.

The passband from 0 Hz to 200 kHz is divided into eight segments. The desired gain at each frequency point is calculated from the inverse CIC magnitude response.

The design weights are:

```text
PASSBAND_WEIGHT = 100
STOPBAND_WEIGHT = 1
```

The stopband target is zero from 350 kHz to the output Nyquist frequency:

```text
625 kHz
```

The floating-point coefficient design must produce:

* exactly 31 taps;
* symmetric coefficients;
* a Type-I linear-phase response;
* combined CIC-to-FIR passband response within ±0.25 dB;
* combined stopband response below -40 dB.

---

## 5. Coefficient Quantization

The floating-point coefficients are quantized to signed 18-bit integers with 17 fractional bits.

The scaling factor is:

```text
2^17 = 131072
```

Quantization uses:

```text
coefficient_integer =
    round_half_away_from_zero(
        coefficient_float × 131072
    )
```

The represented coefficient is:

```text
coefficient_real =
    coefficient_integer / 131072
```

The signed 18-bit integer range is:

```text
-131072 to +131071
```

---

## 6. Frozen Q17 Coefficients

The frozen integer coefficient set is:

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

The coefficients are symmetric:

```text
h[k] = h[30 - k]
```

The centre tap is:

```text
h[15] = 127
```

The integer coefficient sum is:

```text
257
```

The represented coefficient sum is:

```text
257 / 131072
= 0.00196075439453125
```

The ideal normalization sum is:

```text
1 / 512
= 0.001953125
```

The quantized DC normalization therefore has a small positive gain error.

---

## 7. Floating-Point Response Results

The combined floating-point CIC-to-FIR response produces:

```text
DC gain             = 1.000418756
Passband minimum    = -0.003746 dB
Passband maximum    = +0.006157 dB
Passband ripple     = 0.009902 dB
Stopband maximum    = -45.872967 dB
```

Contract result:

```text
Passband target: PASS
Stopband target: PASS
```

---

## 8. Quantized Q17 Response Results

The combined quantized CIC-to-FIR response produces:

```text
DC gain             = 1.003906250
Passband minimum    = -0.070307 dB
Passband maximum    = +0.118005 dB
Passband ripple     = 0.188312 dB
Stopband maximum    = -45.022088 dB
```

Contract result:

```text
Passband target: PASS
Stopband target: PASS
```

The quantized response remains inside the frozen ±0.25 dB passband limit.

---

## 9. Fixed-Point Arithmetic Path

Each FIR input is a signed 21-bit CIC output.

Each multiplication produces:

```text
21-bit input × 18-bit coefficient
= 39-bit signed product
```

The products retain 17 fractional bits.

Thirty-one products are accumulated using a signed 44-bit accumulator.

The arithmetic sequence is:

```text
update sample history
        ↓
multiply each sample by its coefficient
        ↓
wrap each product to 39 bits
        ↓
accumulate each product
        ↓
wrap each addition to 44 bits
        ↓
round once
        ↓
shift right by 17 bits
        ↓
saturate to signed 16 bits
```

The output saturation range is:

```text
-32768 to +32767
```

---

## 10. Rounding Contract

The frozen rounding mode is:

```text
round to nearest, ties away from zero
```

For non-negative accumulator values:

```text
result = (accumulator + 2^16) >> 17
```

For negative accumulator values:

```text
result = -(((-accumulator) + 2^16) >> 17)
```

Rounding occurs once after the full FIR accumulation.

---

## 11. Group Delay

A symmetric 31-tap Type-I FIR has a group delay of:

```text
(TAPS - 1) / 2
= 15 output samples
```

At 1.25 MSPS:

```text
15 / 1,250,000
= 12 microseconds
```

The startup transient caused by the initially zero sample history is part of the defined model and RTL response.

---

## 12. Verification Coverage

The FIR model tests verify:

* coefficient count;
* coefficient symmetry;
* coefficient range;
* deterministic coefficient regeneration;
* rounding around positive and negative half-way cases;
* signed output saturation;
* input boundary validation;
* sample-history reset;
* impulse response;
* group delay;
* positive and negative gain normalization;
* output count;
* floating-point response;
* quantized response;
* floating-point versus quantized response degradation.

The combined CIC-to-FIR tests verify:

* output decimation count;
* wrapper equivalence with manually composed models;
* deterministic reset behaviour;
* unit-step normalization;
* positive full-scale CIC wrapping;
* negative full-scale CIC wrapping;
* in-band sine-frequency preservation.

---

## 13. Frozen Design Status

```text
Floating-point FIR design       PASS
Q17 coefficient quantization    PASS
Fixed-point FIR model           PASS
FIR unit tests                  PASS
CIC-to-FIR pipeline tests       PASS
Frequency-response tests        PASS
```

These coefficients are frozen for project release `v0.1`.

Changing the coefficients, tap count, passband, stopband, coefficient width, fractional width, or rounding policy requires rerunning the complete FIR and CIC-to-FIR verification suite.
