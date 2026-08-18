# Automated Durian Defect Detection & Quality Classification System

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Tauri](https://img.shields.io/badge/Tauri-v2-orange.svg)](https://tauri.app/)
[![YOLOv26](https://img.shields.io/badge/YOLO-v26n-yellow.svg)](https://ultralytics.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

An end-to-end industrial computer vision and automated physical sorting system for durian fruits. Features deep learning defect detection (`crack`, `dark_spot`, `fungus`, `thorn_split`, `reject`), dynamic rule-based grading (Grade A, B, C, Reject), USB HID relay pneumatic gate control, SQLite WAL persistence with rolling hot backups, and an asynchronous background retraining pipeline.

---

## Key Features

- **Split-Process Architecture**: Ultra-responsive Tauri desktop shell (<50 MB RAM) paired with an asynchronous FastAPI computer vision backend.
- **Hardware-Adaptive Vision Engine**: Auto-detects runtime hardware and loads **CoreML** (macOS Apple Silicon), **OpenVINO** (Intel/x86), or **ONNX Runtime** (universal fallback) with $<100\text{ ms}$ latency.
- **Decoupled Rule Engine**: Business grading rules (defect count limits, max surface area ratios, force reject overrides) configured via dynamic JSON profiles without modifying AI weights.
- **Dual Operational Modes**:
  - **Edge Industrial Classifier (`main.py`)**: Real-time camera feed, USB Relay pneumatic sorting gate actuation, SQLite logging, and event WebSockets.
  - **Cloud Workflow Runner (`workflow_app/app.py`)**: Browser-based evaluation dashboard, batch testing with Roboflow Workflows, and Docker deployment.
- **OTA Model Deployment**: Background Celery retraining with MLflow tracking and side-by-side KPI comparison before approving live updates.
- **Comprehensive Reporting**: Instant export of batch sorting analytics to styled Excel (`.xlsx`) and certified PDF (`.pdf`) documents.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│                   Tauri Desktop App                    │
│    - Real-time Video Canvas    - Grade Badge (A/B/C/R) │
│    - Batch & Operator Mgmt     - Settings & OTA Panel  │
└──────────────────────────┬─────────────────────────────┘
                           │  Local WebSockets (/ws/live, /ws/events)
                           │  HTTP REST APIs (Port 8000)
┌──────────────────────────▼─────────────────────────────┐
│                    FastAPI Backend                     │
│  - VisionEngine (CoreML / OpenVINO / ONNX / PyTorch)   │
│  - RuleEngine (config/benchmarks/*.json)               │
│  - RelayController (USB HID VID 0x16c0, PID 0x05df)    │
│  - SQLite Database (data/durian.db with WAL mode)      │
│  - DBBackupService (15-min rolling hot backups)        │
└──────────────────────────┬─────────────────────────────┘
                           │  Background Tasks
┌──────────────────────────▼─────────────────────────────┐
│                 Celery & Redis Worker                  │
│  - Dataset Augmentation (10x industrial distortions)   │
│  - YOLOv26 Retraining & MLflow Experiment Tracking     │
│  - Multi-Format Model Export (CoreML / OpenVINO / ONNX)│
└────────────────────────────────────────────────────────┘
```

For comprehensive design details, see [Architecture Documentation](file:///Users/iminluv/Documents/Durian-classification/docs/architecture.md).

---

## Quick Start & Commands

### 1. Environment Setup
```bash
# Clone the repository
git clone <repository_url>
cd Durian-classification

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Common Execution Commands

| Target | Command | Description |
|---|---|---|
| **Edge Backend** | `python main.py` | Starts FastAPI server, camera capture loop, and relay controller |
| **Desktop UI** | `cd ui/src-tauri && cargo tauri dev` | Launches Tauri operator interface with hot-reloading |
| **Web Workflow App** | `python workflow_app/app.py` | Starts the browser-based workflow evaluator on `http://127.0.0.1:8000` |
| **Share Online** | `./share_online.sh` | Starts workflow app and exposes a secure public HTTPS tunnel |
| **Docker App** | `docker run -p 7860:7860 $(docker build -q .)` | Runs containerized workflow app on port 7860 |
| **CLI Workflow** | `python run_workflow.py --mode all` | Evaluates dataset using Roboflow Workflow API |
| **Model Training** | `python train.py --epochs 50 --device mps` | Trains YOLOv26 model with MLflow experiment tracking |
| **Model Export** | `python export_model.py --weights best.pt` | Exports weights to CoreML, OpenVINO, and ONNX |
| **Model Evaluation**| `python evaluate.py --benchmark --runtime coreml` | Validates against industrial KPI gates (mAP@50, Recall) |
| **Conveyor Sim** | `python simulate_shadow_mode.py 20` | Simulates sorting 20 fruits on conveyor without camera |
| **Celery Worker** | `celery -A tasks.celery_config worker --loglevel=info`| Starts background retraining worker |
| **Unit Tests** | `pytest -v` | Executes automated test suite |

---

## Documentation Directory

| Document | Description |
|---|---|
| [How to Run Guide](file:///Users/iminluv/Documents/Durian-classification/docs/how_to_run.md) | Comprehensive step-by-step setup, run instructions, and troubleshooting guide. |
| [Architecture Specification](file:///Users/iminluv/Documents/Durian-classification/docs/architecture.md) | System design, hardware integrations, multi-runtime vision engine, and API protocols. |
| [Operator Guide (English)](file:///Users/iminluv/Documents/Durian-classification/docs/user_guide_en.md) | Detailed operator manual for desktop & web UI, batch management, and reports. |
| [Operator Guide (Vietnamese)](file:///Users/iminluv/Documents/Durian-classification/docs/user_guide_vi.md) | Tài liệu hướng dẫn vận hành hệ thống phân loại sầu riêng bằng tiếng Việt. |

---

## Architecture Decision Records (ADRs)

Our key engineering decisions are documented in [`docs/decisions/`](file:///Users/iminluv/Documents/Durian-classification/docs/decisions/):

- [ADR-001: Split-Process Architecture (Tauri Frontend + FastAPI Backend)](file:///Users/iminluv/Documents/Durian-classification/docs/decisions/ADR-001-split-process-tauri-fastapi.md)
- [ADR-002: Multi-Runtime Hardware-Adaptive Vision Engine](file:///Users/iminluv/Documents/Durian-classification/docs/decisions/ADR-002-multi-runtime-adaptive-vision-engine.md)
- [ADR-003: Decoupled Rule Engine and Dynamic Benchmark Profiles](file:///Users/iminluv/Documents/Durian-classification/docs/decisions/ADR-003-decoupled-rule-engine-and-benchmark-profiles.md)
- [ADR-004: Dual Deployment Modes (Edge Classifier & Cloud Workflow Runner)](file:///Users/iminluv/Documents/Durian-classification/docs/decisions/ADR-004-dual-mode-edge-classifier-and-workflow-runner.md)
- [ADR-005: SQLite WAL Mode and Automated Rolling Hot Backups](file:///Users/iminluv/Documents/Durian-classification/docs/decisions/ADR-005-sqlite-wal-and-automated-hot-backup.md)

---

## Project Structure

```
Durian-classification/
├── api/                   # FastAPI routes and WebSocket connection manager
├── config/                # System configuration & benchmark rule JSON files
│   └── benchmarks/        # Hot-reloadable grading benchmark profiles
├── core/                  # Core engines (Vision, Rule, Relay, Capture, DB, Backups)
│   └── backends/          # Hardware execution backends (CoreML, OpenVINO, ONNX)
├── docs/                  # System documentation, run guides, and ADRs
│   └── decisions/         # Architecture Decision Records (ADRs)
├── models/                # Production model weights and exported formats
├── reports/               # Excel (.xlsx) and PDF (.pdf) generation services
├── tasks/                 # Celery background tasks & retraining pipeline
├── tests/                 # Automated pytest test suites
├── ui/                    # Tauri desktop application (HTML/JS/CSS frontend + Rust shell)
├── workflow_app/          # Web-based Roboflow workflow evaluator application
├── train.py               # YOLO model training script with MLflow
├── evaluate.py            # KPI gate validation and latency benchmark script
├── export_model.py        # Multi-format model export script
├── simulate_shadow_mode.py# Conveyor belt shadow simulation script
├── share_online.sh        # Quick-start script for localtunnel public access
└── Dockerfile             # Production Docker container definition
```
