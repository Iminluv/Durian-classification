# How to Run — Automated Durian Classification System

This guide provides comprehensive instructions for installing, configuring, and running every subsystem of the **Automated Durian Defect Detection and Quality Classification System**.

---

## Table of Contents

1. [Prerequisites & Environment Setup](#1-prerequisites--environment-setup)
2. [Running the Edge Industrial Classifier (Main System)](#2-running-the-edge-industrial-classifier-main-system)
   - [2.1 Start FastAPI Vision & Hardware Backend](#21-start-fastapi-vision--hardware-backend)
   - [2.2 Launch Tauri Desktop UI](#22-launch-tauri-desktop-ui)
3. [Running the Web-Based Workflow App & Cloud Runner](#3-running-the-web-based-workflow-app--cloud-runner)
   - [3.1 Start Local Workflow Web Server](#31-start-local-workflow-web-server)
   - [3.2 Share Online via Localtunnel](#32-share-online-via-localtunnel)
   - [3.3 Run in Docker Container](#33-run-in-docker-container)
   - [3.4 Run CLI Workflow Evaluator](#34-run-cli-workflow-evaluator)
4. [AI Model Training, Evaluation & Export](#4-ai-model-training-evaluation--export)
   - [4.1 Dataset Augmentation Pipeline](#41-dataset-augmentation-pipeline)
   - [4.2 Model Training with MLflow Tracking](#42-model-training-with-mlflow-tracking)
   - [4.3 Multi-Format Model Export (CoreML / OpenVINO / ONNX / PyTorch)](#43-multi-format-model-export-coreml--openvino--onnx--pytorch)
   - [4.4 Model Validation & KPI Gate Benchmarking](#44-model-validation--kpi-gate-benchmarking)
5. [Asynchronous Celery Retraining Pipeline](#5-asynchronous-celery-retraining-pipeline)
6. [Running Conveyor Belt Shadow Mode Simulation](#6-running-conveyor-belt-shadow-mode-simulation)
7. [Running Automated Tests](#7-running-automated-tests)
8. [Configuration Reference](#8-configuration-reference)
9. [Troubleshooting & FAQs](#9-troubleshooting--faqs)

---

## 1. Prerequisites & Environment Setup

### System Requirements
- **Operating System**: macOS (Apple Silicon M1/M2/M3/M4 or Intel), Windows 10/11 (x86_64), or Ubuntu 20.04+ / Linux
- **Python**: Version `3.10` or `3.11`
- **Node.js & npm** *(for Tauri desktop frontend and localtunnel)*: Node.js 18+ and npm
- **Rust & Cargo** *(for building Tauri desktop app)*: `rustc 1.70+`
- **Redis Server** *(optional, for Celery background retraining)*: Redis 6.0+

### Step 1.1: Clone and Create Virtual Environment
```bash
# Clone the repository
git clone <repository_url>
cd Durian-classification

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On macOS / Linux:
source .venv/bin/activate

# On Windows (PowerShell):
# .venv\Scripts\Activate.ps1
# On Windows (Command Prompt):
# .venv\Scripts\activate.bat
```

### Step 1.2: Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 1.3: Configure Environment Variables
Create or verify your `.env` file in the root directory:
```env
ROBOFLOW_API_KEY=your_roboflow_api_key_here
ROBOFLOW_WORKFLOW_ID=your_roboflow_workflow_id_here
CLOUD_MODE=false
```

---

## 2. Running the Edge Industrial Classifier (Main System)

The Edge Industrial Classifier consists of a **FastAPI backend** (running OpenCV, Vision Engine, Rule Engine, SQLite, and USB Relay drivers) and a **Tauri Desktop UI**.

```
┌────────────────────────────────────────────────────────┐
│                   Tauri Desktop App                    │
│          (HTML5 / Vanilla JS / CSS Glassmorphism)      │
└──────────────────────────┬─────────────────────────────┘
                           │  HTTP REST (Port 8000) &
                           │  WebSockets (/ws/live, /ws/events)
┌──────────────────────────▼─────────────────────────────┐
│                    FastAPI Backend                     │
│  - VisionEngine (CoreML / OpenVINO / ONNX / PyTorch)   │
│  - RuleEngine (config/benchmarks/*.json)               │
│  - RelayController (USB HID VID 0x16c0, PID 0x05df)    │
│  - SQLite Database (data/durian.db with WAL mode)      │
│  - DBBackupService (15-min rolling hot backups)        │
└────────────────────────────────────────────────────────┘
```

### 2.1 Start FastAPI Vision & Hardware Backend

```bash
# Make sure your virtual environment is active
source .venv/bin/activate

# Option A: Direct python execution
python main.py

# Option B: Run via Uvicorn with auto-reload for development
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

- **Backend Address**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **Live Video WebSocket**: `ws://127.0.0.1:8000/ws/live`
- **Sorting Event WebSocket**: `ws://127.0.0.1:8000/ws/events`
- **Health Check**: `http://127.0.0.1:8000/health`

### 2.2 Launch Tauri Desktop UI

```bash
# Navigate to the Tauri directory
cd ui/src-tauri

# Run in development mode (hot reloads UI code)
cargo tauri dev

# Or build the production binary
cargo tauri build
```

> [!NOTE]
> In production releases, the FastAPI backend is packaged as an external sidecar binary (`bin/durian-backend`) within the Tauri app bundle, automatically starting upon application launch.

---

## 3. Running the Web-Based Workflow App & Cloud Runner

For remote browser testing, batch image evaluations, or cloud deployments without local camera/relay hardware.

### 3.1 Start Local Workflow Web Server
```bash
# Activate virtual environment
source .venv/bin/activate

# Run the workflow FastAPI application
python workflow_app/app.py
```
Open your browser at **`http://127.0.0.1:8000`** to access the web evaluation dashboard.

### 3.2 Share Online via Localtunnel
To instantly generate a secure public HTTPS URL for demoing or testing from any device:
```bash
chmod +x share_online.sh
./share_online.sh
```
The terminal will display the live public URL (e.g., `https://durian-classifier-demo.loca.lt`). Press `Ctrl+C` to cleanly stop both the web server and the tunnel.

### 3.3 Run in Docker Container
```bash
# Build the Docker image
docker build -t durian-classifier-workflow .

# Run container on port 7860 (Hugging Face Spaces default)
docker run -d -p 7860:7860 \
  -e ROBOFLOW_API_KEY="your_key" \
  -e ROBOFLOW_WORKFLOW_ID="your_workflow_id" \
  --name durian_workflow_app \
  durian-classifier-workflow

# Access the containerized app
# http://localhost:7860
```

### 3.4 Run CLI Workflow Evaluator
Evaluate the Roboflow Workflow directly from the command line:
```bash
# Evaluate all images in the test set
python run_workflow.py --mode all

# Evaluate a specific image
python run_workflow.py --mode single --image sample_01.jpg

# Evaluate 1 random image
python run_workflow.py --mode random

# Evaluate 1 random image containing multiple defect classes
python run_workflow.py --mode random_multi

# Evaluate N random images
python run_workflow.py --mode random_n --n 10
```

---

## 4. AI Model Training, Evaluation & Export

### 4.1 Dataset Augmentation Pipeline
Enrich training data with industrial distortions (motion blur, lighting shifts, rotations, cutout):
```bash
python -c "from core.augment import DatasetAugmenter; augmenter = DatasetAugmenter(input_dir='durian', output_dir='data/augmented', multiplier=10); augmenter.run()"
```

### 4.2 Model Training with MLflow Tracking
Train the YOLOv26 defect detection model on custom durian classes:
```bash
# Train on Apple Silicon (MPS acceleration)
python train.py --data durian.yaml --epochs 50 --imgsz 640 --batch 16 --device mps

# Train on CUDA GPU (device 0)
python train.py --data durian.yaml --epochs 50 --imgsz 640 --batch 16 --device 0

# Train on CPU
python train.py --data durian.yaml --epochs 50 --imgsz 640 --batch 8 --device cpu
```
- Training runs are logged to `runs/detect/train_durian/` and registered with **MLflow** (`mlflow ui` on port 5000).
- Best weights are automatically saved to `best.pt`.

### 4.3 Multi-Format Model Export (CoreML / OpenVINO / ONNX / PyTorch)
Export the trained PyTorch weights into hardware-optimized deployment formats:
```bash
python export_model.py --weights best.pt --output models/yolov26n_v1
```
This generates:
- `models/yolov26n_v1/coreml/best.mlpackage` (FP16 targeting Apple Neural Engine)
- `models/yolov26n_v1/openvino/best.xml` & `best.bin` (FP32 targeting Intel CPUs)
- `models/yolov26n_v1/best.onnx` (Opset 17 universal fallback)
- `models/yolov26n_v1/best.pt` (Original PyTorch checkpoint)

### 4.4 Model Validation & KPI Gate Benchmarking
Run full test evaluation with latency benchmarking against industrial KPI gates:
```bash
# Evaluate using PyTorch runtime
python evaluate.py --weights best.pt --benchmark --runtime pytorch

# Benchmark CoreML runtime (macOS)
python evaluate.py --weights models/yolov26n_v1/coreml/best.mlpackage --benchmark --runtime coreml

# Benchmark OpenVINO runtime (Intel/x86)
python evaluate.py --weights models/yolov26n_v1/openvino --benchmark --runtime openvino

# Benchmark universal ONNX Runtime
python evaluate.py --weights models/yolov26n_v1/best.onnx --benchmark --runtime onnx
```

#### Industrial KPI Quality Gates
| Metric | Threshold | Target Description |
|---|---|---|
| **mAP@50** | `≥ 70%` | Overall detection precision & recall |
| **Recall (fungus)** | `≥ 85%` | High sensitivity for mold/fungus quarantine defects |
| **Recall (reject)** | `≥ 85%` | Strict rejection of severe rot/deformations |
| **CoreML Latency** | `< 100 ms` | Real-time Apple Silicon throughput |
| **OpenVINO Latency** | `< 200 ms` | Real-time industrial Intel PC throughput |

Results are exported to `evaluation_results.json`.

---

## 5. Asynchronous Celery Retraining Pipeline

The background retraining pipeline allows the system to train a new model asynchronously when operators flag new misclassified images in the field.

### Step 5.1: Start Redis
```bash
# Start Redis in background or standalone terminal
redis-server
```

### Step 5.2: Launch Celery Worker
```bash
celery -A tasks.celery_config worker --loglevel=info
```

### Step 5.3: Trigger Retraining Task
Trigger programmatically in Python:
```python
from tasks.retrain import trigger_retrain_pipeline

task = trigger_retrain_pipeline.delay(epochs=15, batch_size=16)
print(f"Retraining task triggered: {task.id}")
```
Upon completion:
1. Augmented dataset is generated.
2. Model is trained and exported to CoreML, OpenVINO, and ONNX.
3. Validation metrics are generated.
4. A notification is written to `config/pending_model.json`.
5. The Desktop UI displays a pending OTA approval modal comparing old vs new metrics.

---

## 6. Running Conveyor Belt Shadow Mode Simulation

Simulate a factory conveyor sorting run without needing a physical camera or conveyor belt:
```bash
# Simulate 20 fruits passing the sensor at 1.5-second intervals
python simulate_shadow_mode.py 20

# Simulate 50 fruits
python simulate_shadow_mode.py 50
```
During simulation:
- Virtual fruits pass the sensor with various defect configurations.
- The **RuleEngine** calculates grades (`A`, `B`, `C`, `reject`).
- The **RelayController** triggers simulated sorting channels.
- Events are logged in `data/durian.db`.
- Excel and PDF reports can be downloaded immediately:
  - Excel: `http://127.0.0.1:8000/api/reports/<BATCH_ID>/excel`
  - PDF: `http://127.0.0.1:8000/api/reports/<BATCH_ID>/pdf`

---

## 7. Running Automated Tests

Run unit and integration tests using `pytest`:

```bash
# Run all unit tests
pytest -v

# Run rule engine and database tests specifically
pytest tests/test_rule_engine.py tests/test_database.py -v

# Run API and vision tests
pytest tests/test_api.py tests/test_vision_engine.py tests/test_capture.py -v
```

---

## 8. Configuration Reference

All system behaviors are configured via JSON files in `config/`:

| Config File | Description |
|---|---|
| [`config/app.json`](file:///Users/iminluv/Documents/Durian-classification/config/app.json) | Database path, backup frequency, model directory, logging level, relay mock mode. |
| [`config/rules.json`](file:///Users/iminluv/Documents/Durian-classification/config/rules.json) | Active benchmark profile name and defect confidence thresholds (`crack`, `dark_spot`, `fungus`, `thorn_split`, `reject`). |
| [`config/camera.json`](file:///Users/iminluv/Documents/Durian-classification/config/camera.json) | Camera source type (`usb` or `rtsp`), USB index, RTSP URL, target FPS. |
| [`config/benchmarks/standard_qc_v1.json`](file:///Users/iminluv/Documents/Durian-classification/config/benchmarks/standard_qc_v1.json) | Quality grade thresholds per defect (max counts for A/B/C, max area ratio, force reject flags). |

---

## 9. Troubleshooting & FAQs

### Q1: Camera fails to open (`Camera not initialized`)
- Check `config/camera.json`. If using a USB webcam, set `"usb_device_id": 0` (or `1`, `2` if external).
- On macOS, ensure the Terminal or IDE has Camera permissions enabled under **System Settings > Privacy & Security > Camera**.

### Q2: USB Relay gives permissions error or is not found
- If operating without physical relay hardware, set `"relay_mock": true` in `config/app.json`. The system will safely log all relay trigger pulses to the console.
- On Linux, create a udev rule for VID `0x16c0` / PID `0x05df`:
  ```bash
  echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="16c0", ATTRS{idProduct}=="05df", MODE="0666"' | sudo tee /etc/udev/rules.d/99-usb-relay.rules
  sudo udevadm control --reload-rules
  ```

### Q3: PyTorch 2.6+ `weights_only=True` loading error
- All entry points (`train.py`, `evaluate.py`, `export_model.py`) include automatic patches for `torch.load` to support YOLO model structure deserialization.

### Q4: Port 8000 is already in use
- Check running processes: `lsof -i :8000`
- Terminate previous instances: `kill -9 <PID>` or launch FastAPI on a different port: `uvicorn main:app --port 8001`.
