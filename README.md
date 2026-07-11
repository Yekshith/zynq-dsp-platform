# Zynq DSP Validation Platform

[![CI](https://github.com/Yekshith/zynq-dsp-platform/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Yekshith/zynq-dsp-platform/actions/workflows/ci.yml)

This is a portfolio-grade project being built and released in stages.

A Znyq-7000 platform that captures samples from a parallel ADC in its own clock domain, crosses them through an asynchronous FIFO, processes them in a fixed-point CIC+FIR decimation pipeline verified bit-exact against a Python golden model, arbitrates two stream sources into a single AXI-DMA channel under an AXI-Lite register map, buffers into PS DDR, and streams processed frames over UDP to a live host display - with a cocotb + SVA +VUnit verification stack running in Docker CI, ILA-captured bus evidence, and a documented timing-closure exercise.


## Current Status

| Milestone | Status | Evidence |
|---|---:|---|
| Phase 0: repo skeleton |  Done | Folder structure, `.gitignore`, README scaffold |
| Phase 0.2: Docker CI shell |  Done | GitHub Actions builds Docker image and runs pytest |
| Phase 1.1: CIC golden model | Started | In Progress |
| Phase 1.2: FIR golden model |  Pending | Not started |
| Phase 1.3+: RTL verification |  Pending | Not started |

## Demo

Planned for Phase 4. The first public demo will show processed frames streamed from the ZedBoard PS to a host-side live spectrum display.

## Verification Summary

Current verification scope is infrastructure-only.

| Test area | Tool | Status |
|---|---|---|
| CI container build | Docker |  Passing |
| Python test discovery | pytest |  Passing |
| Placeholder smoke test | pytest |  Passing |
| CIC golden-model tests | pytest |  Next |
| RTL simulation | GHDL/cocotb |  Pending |
| VUnit tests | VUnit |  Pending |
| Hardware evidence | ZedBoard/ILA |  Pending |

## On-Chip Evidence

Planned for Phase 3. Evidence will include ILA captures of AXI-stream handshakes, DMA backpressure, and frame movement into PS DDR.

## Timing Closure

Planned for Phase 3.5. This section will document a deliberate timing-closure exercise with before/after WNS numbers.

## Architecture

Initial architecture documentation will be added in Phase 1.1 when CIC word lengths and fixed-point behavior are defined.

See: [`docs/architecture.md`](docs/architecture.md)

## Requirements traceability

The requirements matrix will be seeded in Phase 1.5 after the first CIC/FIR model and RTL verification milestones are complete.

See: [`docs/requirements.md`](docs/requirements.md)

## Build & Run

### Run Locally

Build the CI image:

```bash
docker build -t zynq-ci ci/

----

*Built as an engineering portfolio project.*  
