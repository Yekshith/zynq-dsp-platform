# Zynq DSP Validation Platform

A Znyq-7000 platform that captures samples from a parallel ADC in its own clock domain, crosses them through an asynchronous FIFO, processes them in a fixed-point CIC+FIR decimation pipeline verified bit-exact against a Python golden model, arbitrates two stream sources into a single AXI-DMA channel under an AXI-Lite register map, buffers into PS DDR, and streams processed frames over UDP to a live host display - with a cocotb + SVA +VUnit verification stack running in Docker CI, ILA-captured bus evidence, and a documented timing-closure exercise.

## Demo

## Verification Summary

## On-Chip Evidence

## Timing Closure

## Architecture

## Requirements traceability

## Build & Run


----

*Built as an engineering portfolio project.*  
