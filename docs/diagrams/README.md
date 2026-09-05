# Durian Classification System — Architecture & Workflow Diagrams

This directory contains clear, standard diagrams (User Flows, Sequence Diagrams, UML Diagrams, State Machines, and Flowcharts) to introduce the system workflows, user journeys, and component interactions.

---

## Table of Contents

1. [User Flow Diagram (Operator & Evaluator Journeys)](#1-user-flow-diagram)
2. [UML Use Case Diagram (Roles & Capabilities)](#2-uml-use-case-diagram)
3. [Real-Time Sorting Sequence Diagram](#3-sequence-diagram--real-time-fruit-sorting)
4. [OTA Model Retraining Sequence Diagram](#4-sequence-diagram--ota-model-retraining--approval)
5. [UML Class Diagram (Core Architecture)](#5-uml-class-diagram--core-engines)
6. [Batch Lifecycle State Machine Diagram](#6-batch-lifecycle-state-machine-diagram)
7. [Hardware-Adaptive Vision Engine Flowchart](#7-vision-engine-runtime-selection-flowchart)

---

## 1. User Flow Diagram

Visualizes the step-by-step path for both **Factory Operators** (Edge Mode) and **QA / Remote Evaluators** (Cloud/Workflow Mode).

```mermaid
flowchart TD
    Start(["User Opens System"])
    Mode{"Select Execution Mode"}

    Start --> Mode

    %% --- Factory Operator Journey ---
    subgraph EdgeJourney ["Edge Industrial Mode (main.py + Tauri)"]
        Launch1["Run: python main.py"]
        TauriUI["Open Tauri Desktop Application"]
        StartBatch["Start Batch Session\n(Enter Operator Name & Batch ID)"]
        LiveFeed["Monitor Live Stream\n(Base64 JPEG Annotations @ 10 FPS)"]
        GradeFruit["VisionEngine + RuleEngine\nAssign Grade: A / B / C / REJECT"]
        GateActuate["USB Relay Trigger\nPneumatic Gates (Ch 1-4) Actuate"]
        MoreCheck{"More Fruits on Conveyor?"}
        StopBatch["Stop Batch Session"]
        ExportReports["Export Batch Reports\n(.xlsx Excel & .pdf Certified)"]
        FinishEdge(["Batch Completed"])

        Launch1 --> TauriUI --> StartBatch --> LiveFeed --> GradeFruit --> GateActuate --> MoreCheck
        MoreCheck -- "Yes" --> LiveFeed
        MoreCheck -- "No" --> StopBatch --> ExportReports --> FinishEdge
    end

    %% --- QA & Remote Evaluator Journey ---
    subgraph CloudJourney ["Web and Cloud Mode (workflow_app/app.py)"]
        Launch2["Run: python workflow_app/app.py"]
        BrowserUI["Open Web Browser\n(http://127.0.0.1:8000 or Public Tunnel)"]
        UploadImages["Upload Durian Images / Datasets"]
        RunWorkflow["Execute Roboflow Cloud Workflow"]
        InspectResults["Inspect Detections, Defect Classes\n& Confidence Scores"]
        FinishCloud(["Inspection Finished"])

        Launch2 --> BrowserUI --> UploadImages --> RunWorkflow --> InspectResults --> FinishCloud
    end

    Mode -- "Edge Sorting Line" --> EdgeJourney
    Mode -- "QA / Remote Audit" --> CloudJourney
```

---

## 2. UML Use Case Diagram

Defines system actors and their interactions with system capabilities.

```mermaid
graph LR
    %% Actors
    Operator(["Operator"])
    QAManager(["QA Manager"])
    DataScientist(["Data Scientist"])
    RemoteAuditor(["Remote Auditor"])

    %% Subgraph boundary
    subgraph DurianSystem ["Automated Durian Classification System"]
        UC1(["UC-01: Start / Stop Sorting Batch"])
        UC2(["UC-02: Monitor Live Video & Badges"])
        UC3(["UC-03: Download Excel / PDF Reports"])
        UC4(["UC-04: Configure & Hot-Reload Benchmark Rules"])
        UC5(["UC-05: Review & Approve OTA Model Deployments"])
        UC6(["UC-06: Trigger Background Retraining (Celery)"])
        UC7(["UC-07: Monitor MLflow Experiment Metrics"])
        UC8(["UC-08: Web-Based Image Workflow Evaluation"])
    end

    Operator --> UC1
    Operator --> UC2
    Operator --> UC3

    QAManager --> UC3
    QAManager --> UC4
    QAManager --> UC5

    DataScientist --> UC6
    DataScientist --> UC7
    DataScientist --> UC5

    RemoteAuditor --> UC8
    RemoteAuditor --> UC3
```

---

## 3. Sequence Diagram — Real-Time Fruit Sorting

Illustrates the millisecond-level interaction cycle from optical capture to pneumatic sorting gate actuation.

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Operator
    participant UI as Tauri Desktop UI
    participant Server as FastAPI Core (main.py)
    participant Capture as CameraCapture
    participant Vision as VisionEngine
    participant Rules as RuleEngine
    participant Relay as RelayController (USB HID)
    participant DB as SQLite WAL

    Operator->>UI: Click "Start Batch"
    UI->>Server: POST /api/batch/start {batch_id, operator}
    Server->>DB: INSERT INTO batches ...
    Server-->>UI: Batch Started (200 OK)

    loop Continuous Sorting Loop
        Capture->>Capture: Grab video frame from camera
        Capture->>Vision: Preprocessed frame matrix
        Vision->>Vision: Hardware inference (<100ms)
        Vision-->>Capture: Detections [{class, bbox, conf}]

        Capture->>Rules: grade_fruit(detections, width, height)
        Rules->>Rules: Check force_reject (e.g. fungus)
        Rules->>Rules: Evaluate defect limits & areas (A -> B -> C -> REJECT)
        Rules-->>Capture: Result {grade, reasons, defect_counts}

        Capture->>Relay: actuate_gate(grade)
        Relay-->>Relay: Pulse 50ms (Channel 1, 2, 3, or 4)

        Capture->>DB: INSERT INTO detection_events ...
        Capture->>Server: Broadcast event & live frame
        Server-->>UI: WebSocket (/ws/events & /ws/live)
        UI-->>Operator: Render Bounding Boxes & Grade Badge (A/B/C/REJECT)
    end

    Operator->>UI: Click "Stop Batch"
    UI->>Server: POST /api/batch/stop
    Server->>DB: UPDATE batches SET end_time ...
    UI->>Server: GET /api/reports/{batch_id}/excel
    Server-->>UI: Download report.xlsx
```

---

## 4. Sequence Diagram — OTA Model Retraining & Approval

Demonstrates zero-downtime model updates with human-in-the-loop KPI validation.

```mermaid
sequenceDiagram
    autonumber
    actor QA as QA / ML Engineer
    participant UI as Tauri UI (Settings)
    participant API as FastAPI Server
    participant Celery as Celery Retrain Task
    participant Augment as core/augment.py
    participant Trainer as YOLOv26 Trainer
    participant Exporter as export_model.py
    participant Evaluator as evaluate.py
    participant Vision as VisionEngine

    QA->>UI: Click "Retrain Model on New Samples"
    UI->>API: POST /api/model/retrain
    API->>Celery: retrain_task.delay(epochs=50)
    API-->>UI: Retraining Dispatched (Task ID)

    Celery->>Augment: 10x industrial distortions (lighting, blur, rot)
    Augment-->>Trainer: Augmented dataset prepared
    Trainer->>Trainer: Train YOLOv26 & log metrics to MLflow
    Trainer-->>Exporter: best.pt weights
    Exporter->>Exporter: Export CoreML, OpenVINO, ONNX to models/pending_model/
    Exporter->>Evaluator: Validate KPI gates (mAP@50, Recall)
    Evaluator-->>API: Write config/pending_model.json
    API-->>UI: WebSocket event: "NEW_MODEL_AVAILABLE"

    UI-->>QA: Show Side-by-Side KPI Comparison (Old vs New)

    alt Approved by QA
        QA->>UI: Click "Approve & Deploy"
        UI->>API: POST /api/model/update/approve
        API->>Vision: Hot-swap active weights path
        Vision-->>API: Weights Reloaded (Zero Server Restart)
        API-->>UI: Deployment Confirmed
    else Rejected by QA
        QA->>UI: Click "Reject"
        UI->>API: POST /api/model/update/reject
        API->>API: Purge staging directory (models/pending_model/)
        API-->>UI: Update Dismissed
    end
```

---

## 5. UML Class Diagram — Core Engines

Shows the structural relationships, fields, and public methods across backend modules.

```mermaid
classDiagram
    direction TB

    class VisionEngine {
        +str runtime
        +str device
        +object model
        +__init__(model_dir)
        +predict(frame) list~dict~
        -_select_runtime() str
        -_load_coreml()
        -_load_openvino()
        -_load_onnx()
    }

    class RuleEngine {
        +Path rules_path
        +str active_benchmark_name
        +dict benchmark_data
        +__init__(rules_path)
        +load_rules()
        +load_benchmark()
        +check_updates()
        +grade_fruit(detections, frame_w, frame_h) dict
    }

    class CameraCapture {
        +str source
        +bool is_running
        +int target_fps
        +start()
        +stop()
        +capture_loop()
    }

    class RelayController {
        +object device
        +bool mock_mode
        +__init__(mock)
        +actuate_gate(grade) bool
        +send_command(cmd) bool
        +reset_all()
    }

    class DatabaseManager {
        +str db_path
        +__init__(db_path)
        +insert_detection(data) int
        +start_batch(batch_id, operator)
        +stop_batch(batch_id)
        +get_batch_summary(batch_id) dict
        +checkpoint()
    }

    class DBBackupService {
        +str db_path
        +str backup_dir
        +int interval_seconds
        +int max_backups
        +start()
        +stop()
        +create_backup() str
        -_prune_backups()
    }

    class FastAPIApp {
        +VisionEngine vision_engine
        +RuleEngine rule_engine
        +RelayController relay_ctrl
        +DatabaseManager db_manager
        +CameraCapture camera_capture
        +startup_event()
        +shutdown_event()
    }

    FastAPIApp o-- VisionEngine : manages
    FastAPIApp o-- RuleEngine : manages
    FastAPIApp o-- RelayController : manages
    FastAPIApp o-- DatabaseManager : manages
    FastAPIApp o-- CameraCapture : runs
    DatabaseManager ..> DBBackupService : coordinates with
    CameraCapture --> VisionEngine : feeds frames
    CameraCapture --> RuleEngine : submits detections
    CameraCapture --> RelayController : triggers channel
    CameraCapture --> DatabaseManager : logs records
```

---

## 6. Batch Lifecycle State Machine Diagram

Describes the internal state machine governing sorting batches, concurrency locks, and report generations.

```mermaid
stateDiagram-v2
    [*] --> Idle: System Startup / DB Initialized

    state Idle {
        [*] --> Ready
        Ready: Camera in preview mode
        Ready: Ready for operator input
    }

    Idle --> Running: POST /api/batch/start (operator, batch_id)

    state Running {
        [*] --> Ingesting
        Ingesting --> Inferencing: Frame Captured
        Inferencing --> Grading: Bounding Boxes Detected
        Grading --> Actuating: Assign A/B/C/Reject
        Actuating --> Ingesting: Pulse Relay & Log DB
    }

    Running --> Paused: Temporary Conveyor Hold
    Paused --> Running: Resume Conveyor

    Running --> Stopped: POST /api/batch/stop

    state Stopped {
        [*] --> FinalizingSummary
        FinalizingSummary --> GeneratingReports: Aggregate Batch KPIs
        GeneratingReports --> AvailableForDownload: Create .xlsx & .pdf
    }

    Stopped --> Idle: Reset / Start New Batch
```

---

## 7. Vision Engine Runtime Selection Flowchart

Explains how `VisionEngine` achieves hardware-adaptive zero-configuration execution across macOS, Intel/AMD x86, and universal devices.

```mermaid
flowchart TD
    Init(["VisionEngine Initialization"])
    CheckPlatform{"System Platform &\nArchitecture?"}

    CheckPlatform -- "Darwin (macOS)\nApple Silicon (arm64)" --> CheckCoreML{"CoreML Model Exists?\n(best.mlpackage)"}
    CheckCoreML -- Yes --> InitCoreML["Load CoreML Runtime\n(Apple Neural Engine / Metal)\nTarget: <80 ms"]
    CheckCoreML -- No --> CheckONNX

    CheckPlatform -- "Linux / Windows\n(x86_64 CPU/GPU)" --> CheckOpenVINO{"OpenVINO Model Exists?\n(best.xml / best.bin)"}
    CheckOpenVINO -- Yes --> InitOpenVINO["Load OpenVINO Runtime\n(AVX-512 / VNNI / Iris)\nTarget: <160 ms"]
    CheckOpenVINO -- No --> CheckONNX

    CheckPlatform -- "Other / Generic" --> CheckONNX{"ONNX Model Exists?\n(best.onnx)"}
    CheckONNX -- Yes --> InitONNX["Load ONNX Runtime\n(Universal CPU / CUDA)\nTarget: <250 ms"]
    CheckONNX -- No --> InitMock["Load Mock Fallback Engine\n(For CI/CD & Unit Tests)"]

    InitCoreML --> Ready(["VisionEngine Active & Ready"])
    InitOpenVINO --> Ready
    InitONNX --> Ready
    InitMock --> Ready

    style InitCoreML fill:#2d6a4f,color:#fff
    style InitOpenVINO fill:#1d3557,color:#fff
    style InitONNX fill:#6b4226,color:#fff
    style InitMock fill:#555,color:#fff
    style Ready fill:#2d6a4f,color:#fff
```
