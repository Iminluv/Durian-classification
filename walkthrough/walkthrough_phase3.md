# Walkthrough: Phase 3 — Core Application Development

This walkthrough details the achievements and files created during the completion of **Phase 3: Core Application Development**.

## 1. Vision Engine & Platform Routing

- **Vision Engine**: Created [vision_engine.py](file:///Users/iminluv/Documents/New%20project/core/vision_engine.py) to automatically inspect platform details at startup and load the correct backend:
  - **macOS ARM64**: CoreML (Neural Engine acceleration) utilizing [coreml_backend.py](file:///Users/iminluv/Documents/New%20project/core/backends/coreml_backend.py).
  - **Windows/Intel**: OpenVINO (CPU/GPU acceleration) utilizing [openvino_backend.py](file:///Users/iminluv/Documents/New%20project/core/backends/openvino_backend.py).
  - **ONNX fallback**: General fallback utilizing [onnx_backend.py](file:///Users/iminluv/Documents/New%20project/core/backends/onnx_backend.py).
- **Mock fallback**: Resolves execution before weights are compiled by running a mock fallback that returns empty detections.

## 2. Rule Engine & Grading

- **Rule Engine**: Created [rule_engine.py](file:///Users/iminluv/Documents/New%20project/core/rule_engine.py) matching detections against user-defined benchmarks:
  - Evaluates bbox dimensions against relative frame sizes to enforce area caps.
  - Grade checks evaluated in order: A → B → C → Reject.
  - **Config Hot-Reloading**: Automatically checks file modification timestamps (`rules.json` and active benchmark file) during evaluation to load updates immediately without application restarts.

## 3. Database & Periodic Backups

- **Database Manager**: Created [database.py](file:///Users/iminluv/Documents/New%20project/core/database.py) using SQLite:
  - **WAL Mode**: Enabled Write-Ahead Logging alongside Synchronous Normal settings for high performance and power-cut safety.
  - **Graceful Shutdown**: Runs a WAL checkpoint (`wal_checkpoint(TRUNCATE)`) on termination signals to merge logs back to the database.
- **Backup Service**: Created [db_backup.py](file:///Users/iminluv/Documents/New%20project/core/db_backup.py) spawning a daemon thread that periodically copies database archives to `data/backups/`, retaining the last N copies.

## 4. Relay Sorting Controller

- **Relay Controller**: Created [relay_controller.py](file:///Users/iminluv/Documents/New%20project/core/relay_controller.py) mapping grades (A, B, C, Reject) to USB HID channels (1, 2, 3, 4):
  - **Windows Production**: Opens the raw USB HID device using VID/PID.
  - **macOS/Mock Fallback**: Simulates relay triggers to console to prevent driver import crashes during developer testing.

## 5. FastAPI & WebSockets Integration

- **App Server**: Created [main.py](file:///Users/iminluv/Documents/New%20project/main.py) coordinating APIs, WebSockets, and loop threads.
- **REST Endpoints**: Created [routes.py](file:///Users/iminluv/Documents/New%20project/api/routes.py) exposing health, paginated history, batch session starts/stops, and rules updating.
- **Live WS feed**: Created [websocket.py](file:///Users/iminluv/Documents/New%20project/api/websocket.py) broadcasting annotated base64 JPEGs (10 FPS loop) and JSON sorting events to clients.
- **Sorting Coordinator Loop**: Video processing coordinator that analyzes frames, triggers relays, and logs entries in the SQLite DB under a cooldown constraint (2.5 seconds per sorting item) to mimic real conveyor behaviors.

## 6. Asynchronous Retrain Pipeline

- **Celery Tasks**: Created [retrain.py](file:///Users/iminluv/Documents/New%20project/tasks/retrain.py) and [celery_config.py](file:///Users/iminluv/Documents/New%20project/tasks/celery_config.py):
  - Connects to a Redis broker to queue training tasks in the background.
  - Executes dataset augmentation, model retraining, and exports compilation.
  - **OTA operator verification**: Saves results to `config/pending_model.json` to allow the UI to request explicit confirmation before replacing weights.

## 7. Verification Results

### Unit and Integration Tests
We created comprehensive unit tests verifying rules, DB commits, API routes, and platform routing:
- [test_rule_engine.py](file:///Users/iminluv/Documents/New%20project/tests/test_rule_engine.py)
- [test_database.py](file:///Users/iminluv/Documents/New%20project/tests/test_database.py)
- [test_vision_engine.py](file:///Users/iminluv/Documents/New%20project/tests/test_vision_engine.py)
- [test_api.py](file:///Users/iminluv/Documents/New%20project/tests/test_api.py)

Running the test suite yields:
```bash
Ran 16 tests in 10.150s

OK
```
*(Includes mock, capture, and phase 2 unit tests).*
