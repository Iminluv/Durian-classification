# ADR-002: Multi-Runtime Hardware-Adaptive Vision Engine

## Status
Accepted

## Date
2026-05-21

## Context
Deploying computer vision models to edge packing facilities requires running on diverse hardware:
- **macOS Apple Silicon (ARM64)**: Used for rapid development, testing, and field demonstrations.
- **Intel / AMD Industrial Edge PCs (x86_64)**: Standard hardware mounted inside factory electrical enclosures.
- **Generic Linux / Cloud VMs**: Used for CI/CD, remote simulations, and Docker containers.

Standard PyTorch (`torch`) inference exhibits significant latency overhead on CPU (often >350 ms per frame) and consumes excessive memory, violating the industrial sorting target latency ($< 100\text{ ms}$ on Apple Silicon, $< 200\text{ ms}$ on Intel x86).

## Decision
Implement a **Multi-Runtime Hardware-Adaptive Vision Engine** (`core/vision_engine.py` and `export_model.py`) that exports PyTorch checkpoints into three target execution formats and auto-detects the optimal runtime at startup:

1. **Apple Silicon macOS**: Loads **CoreML** (`.mlpackage` with FP16 precision) compiled for the Apple Neural Engine (ANE) and Apple Silicon GPU.
2. **Intel / AMD Windows & Linux**: Loads **OpenVINO** (`.xml`/`.bin` with FP32/FP16 precision) utilizing AVX-512 / VNNI vector acceleration.
3. **Universal Fallback**: Loads **ONNX Runtime** (`.onnx` Opset 17 with graph simplification) for general-purpose execution across any architecture.
4. **Mock Fallback**: Initializes an empty mock backend if weights are missing during initial setup or isolated unit testing.

## Alternatives Considered

### 1. Single ONNX Runtime for All Platforms
- **Pros**: Only one model format to export and maintain.
- **Cons**: ONNX on Apple Silicon lacks native Apple Neural Engine (ANE) optimization and runs significantly slower than CoreML FP16 (180 ms vs 65 ms).
- **Rejected**: Suboptimal hardware utilization on macOS development and demonstration devices.

### 2. Pure PyTorch (`torch.jit.trace` / `torchscript`)
- **Pros**: No external model conversion step.
- **Cons**: High memory footprint (~1.5 GB RAM for PyTorch runtime), missing Intel OpenVINO hardware optimizations, slower latency.
- **Rejected**: Fails industrial latency KPI gates on edge hardware.

## Consequences
- **Positive**:
  - CoreML achieves sub-80 ms latency on Apple Silicon M-series chips.
  - OpenVINO achieves sub-160 ms latency on Intel Core i5/i7 industrial edge PCs.
  - Transparent runtime auto-selection: zero configuration or code modifications required when switching deployment targets.
  - Comprehensive model export tool (`export_model.py`) automates generating all formats in a single command.
- **Negative / Trade-offs**:
  - Model export pipeline must generate and package multiple model directories (`models/yolov26n_v1/{coreml, openvino, best.onnx}`).
  - Testing matrix must validate inference across all three runtime backends.
