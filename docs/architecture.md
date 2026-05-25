# Automated Durian Classification System — Architecture Design

This document details the system design, hardware integrations, and API messaging protocols.

---

## 1. System Overview

The application utilizes a split-process architecture to decouple real-time computer vision from the desktop interface:

```
┌────────────────────────────────────────────────────────┐
│                   Tauri Frontend                       │
│    - Render Video Canvas      - Manage Batches         │
│    - Large Grade Badge        - Settings & OTA panel   │
└──────────────────────────┬─────────────────────────────┘
                           │
                 REST & WebSockets APIs
                           │
┌──────────────────────────▼─────────────────────────────┐
│                    FastAPI Backend                     │
│  - VisionEngine           - SQLite DB (WAL)            │
│  - RuleEngine             - DB Backup thread           │
│  - RelayController        - Celery Worker (Redis)      │
└────────────────────────────────────────────────────────┘
```

- **Tauri Desktop Shell**: A lightweight wrapper written in Rust, loading a fast, responsive dark-themed HTML/JS/CSS client.
- **FastAPI Backend**: A local Python webserver executing vision models, querying the local database, and controlling physical hardware relays.
- **Celery & Redis Retraining**: An asynchronous worker pipeline triggered when new labeled samples are available, exporting models to multiple formats.

---

## 2. Component Details

### 2.1 Vision Engine
The Vision Engine auto-detects the hardware architecture at startup:
- **Mac Dev (Apple Silicon)**: Loads the **CoreML** runtime (`.mlpackage`) targeting the Apple Neural Engine.
- **Windows Production (Intel/x86)**: Loads the **OpenVINO** runtime (`.xml`/`.bin`) for hardware-accelerated CPU inference.
- **Universal Fallback**: Loads the **ONNX Runtime** if specialized weights or libraries are missing.

### 2.2 Rule Engine & Benchmark Profiles
Decouples grading logic from classification. Bounding boxes are graded at runtime based on the selected Benchmark profile:
- Benchmarks are saved as JSON files in `config/benchmarks/`.
- Configures max counts, max area ratios, and force-reject overrides per defect.
- File watchers allow configuration hot-reloading without backend restarts.

### 2.3 USB HID Relay Controller
Communicates directly with a USB relay module (VID `0x16c0`, PID `0x05df`).
- Routes grades (`A`, `B`, `C`, `reject`) to distinct physical output channels (1 to 4) to actuate sorting gates.
- Emulates relay triggers via console logs when running on Mac development environments.

---

## 3. Communication Protocols

### 3.1 Live Camera Feed WebSocket (`ws://127.0.0.1:8000/ws/live`)
Provides a lightweight base64 MJPEG stream. The backend grabs a camera frame, runs inference, draws annotated bounding boxes, JPEG encodes, and broadcasts the frame.
- **Payload**: Raw Base64 string of the JPEG frame.

### 3.2 Event Notification WebSocket (`ws://127.0.0.1:8000/ws/events`)
Broadcasts sorting results immediately when a fruit passes the detection sensor:
- **Payload Schema**:
  ```json
  {
    "event_type": "detection",
    "batch_id": "BATCH_102",
    "grade": "B",
    "reasons": ["crack count (1) exceeded limits for Grade A"],
    "detections": [
      {"class": "crack", "bbox": [120, 150, 40, 25], "confidence": 0.85}
    ],
    "timestamp": "2026-05-25 18:11:45"
  }
  ```
