# Walkthrough: Phase 1 — Data Collection & Preparation

This walkthrough details the achievements and files created during the completion of **Phase 1: Data Collection & Preparation**.

## 1. Directory Structure Initialized

The project layout has been initialized under the workspace `/Users/iminluv/Documents/New project`:
- `config/` — Configuration settings and templates
- `core/` — Core capture, augmentation, and logging logic
- `data/` — Ignored data workspace (managed by DVC/Gitignore)
- `models/` — Ignored models workspace
- `tests/` — Automated unit test suites

## 2. Configuration & Infrastructure Setup

We created the following configuration files:
- [camera.json](file:///Users/iminluv/Documents/New%20project/config/camera.json): Settings for RTSP/UVC camera capture, motion-detection thresholds, and frame rates.
- [rules.json](file:///Users/iminluv/Documents/New%20project/config/rules.json): Default detection confidence thresholds and pointer to the active benchmark.
- [standard_qc_v1.json](file:///Users/iminluv/Documents/New%20project/config/benchmarks/standard_qc_v1.json): Default quality control rule settings mapping defect counts/areas to grades.
- [app.json](file:///Users/iminluv/Documents/New%20project/config/app.json): App-level parameters (log levels, database path, backup schedules).
- [label_studio_config.xml](file:///Users/iminluv/Documents/New%20project/config/label_studio_config.xml): Configuration xml for visual bounding boxes annotation in Label Studio (5 classes: `crack`, `dark_spot`, `fungus`, `thorn_split`, `reject`).
- [durian.yaml](file:///Users/iminluv/Documents/New%20project/durian.yaml): Dataset description file for training YOLOv8/YOLOv26 models.

## 3. Core Capture & Augmentation Pipelines

We implemented:
- [logger.py](file:///Users/iminluv/Documents/New%20project/core/logger.py): A structured JSON-format python logger.
- [capture.py](file:///Users/iminluv/Documents/New%20project/core/capture.py): High-performance OpenCV capture tool that monitors frames for motion anomalies to trigger saving image captures.
- [augment.py](file:///Users/iminluv/Documents/New%20project/core/augment.py): An Albumentations data augmentation utility that expands the training dataset size by generating transformed image/bbox files, while copying validation/test splits raw.

## 4. DVC Pipeline Setup

We initialized DVC and built the augmentation pipeline stage:
- [dvc.yaml](file:///Users/iminluv/Documents/New%20project/dvc.yaml): Tracks `core/augment.py` and input dataset folders.
- Ran `dvc repro` to process the dataset and generate output directory `data/augmented`.
- Untracked files inside `data/` and `models/` were added to `.gitignore` to prevent committing raw data to git.

## 5. Verification Results

### Unit Tests
We created unit test suites to verify configuration parsing and math logic:
- [test_capture.py](file:///Users/iminluv/Documents/New%20project/tests/test_capture.py)
- [test_augment.py](file:///Users/iminluv/Documents/New%20project/tests/test_augment.py)

Running these tests resulted in:
```bash
Ran 6 tests in 0.028s

OK
```

### Git Tag
All files, configs, tests, and DVC lock files have been committed to git, and the repository was tagged as:
- `dataset-v1.0`
