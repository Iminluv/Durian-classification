# Walkthrough: Phase 2 — Model v1 Training

This walkthrough details the achievements and files created during the completion of **Phase 2: Model v1 Training**.

## 1. Dataset Configuration Refined

- **Absolute Paths**: Refined [durian.yaml](file:///Users/iminluv/Documents/New%20project/durian.yaml) to use the absolute path `/Users/iminluv/Documents/New project/data/augmented` for dataset resolution. This prevents `ultralytics` from falling back to the global `datasets_dir` (which is typically `/Users/iminluv/Documents/datasets/`) and resolved the dataset directory lookup issue.

## 2. Model Training Script

- **Training Script**: Created [train.py](file:///Users/iminluv/Documents/New%20project/train.py) with the following features:
  - **MLflow Integration**: Auto-logging parameters, loss functions, metrics, and best weights artifacts.
  - **Auto-Device Selection**: Checks for device availability in order: Apple Silicon MPS (Metal Performance Shaders) → CUDA GPU → CPU.
  - **Loss Weights Configuration**: Standard inputs optimized for high recall on critical classes (`fungus` and `reject`).
  - **Pre-trained Weight Download/Load**: Attempts to load local `yolov26n.pt` weights and automatically downloads it if not found, with a fallback to training from scratch using YOLO configuration structure.

## 3. Multi-Format Model Exporter

- **Exporter Script**: Created [export_model.py](file:///Users/iminluv/Documents/New%20project/export_model.py) for compiling the best PyTorch model into target inference formats:
  - **ONNX**: Universal fallback exported with `opset=17` and ONNX Simplifier enabled.
  - **OpenVINO IR**: FP32 (`half=False`) XML/BIN format for Windows production systems.
  - **CoreML**: FP16 (`half=True`) `.mlpackage` package for macOS development and testing environments.

## 4. Evaluation Tool & KPI Checker

- **Evaluation Script**: Created [evaluate.py](file:///Users/iminluv/Documents/New%20project/evaluate.py) to perform:
  - **Recall KPI Check**: Verifies that recall scores on the `reject` (class 4) and `fungus` (class 2) splits are both $\ge 85\%$.
  - **mAP KPI Check**: Verifies overall mAP@50 is $\ge 70\%$.
  - **Latency Benchmarking**: Measures inference times over multiple runs and checks if targets (<200ms for OpenVINO on Intel i5, <100ms for CoreML on Apple M-series) are satisfied.

## 5. Compatibility Patches

- **PyTorch 2.6 weights_only Patch**: Implemented a global patch overriding `torch.load` to default `weights_only=False`. This prevents security unpickling errors under PyTorch 2.6+ when loading custom Ultralytics classes (e.g. `DetectionModel`).

## 6. Verification Results

### Unit Tests
We created unit test suite [test_phase2.py](file:///Users/iminluv/Documents/New%20project/tests/test_phase2.py) to mock YOLO models/mlflow and verify code execution logic:
- Mock validation output matches recall constraints
- Mock model exports route correct files to the right folders
- Mock training sets correct parameters

Running the tests yields:
```bash
Ran 3 tests in 1.919s

OK
```

### Pipeline Training Run
We executed training locally for 1 epoch to verify the end-to-end code integration:
```bash
./.venv/bin/python train.py --epochs 1
```
This successfully downloaded `yolov26n.pt`, validated the dataset path under `data/augmented/`, ran training with MPS acceleration on the Apple Silicon GPU, and generated local weights.
