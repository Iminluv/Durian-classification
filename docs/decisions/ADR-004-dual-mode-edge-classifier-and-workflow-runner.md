# ADR-004: Dual Deployment Modes — Edge Industrial Classifier & Web Cloud Workflow Runner

## Status
Accepted

## Date
2026-05-23

## Context
The project serves two distinct operational use cases:
1. **On-Premise Industrial Packing Facility**: Requires a live camera stream, millisecond-precision pneumatic gate actuation via USB Relay, local SQLite persistence, and a native desktop interface (`main.py` + Tauri).
2. **Remote QA / Client Evaluation / Cloud Benchmarking**: Requires evaluating datasets against Roboflow cloud workflows, uploading custom sample images via browser, testing workflow parameters without local camera hardware, and hosting live web demos on Hugging Face Spaces or secure tunnels (`workflow_app/app.py` + `run_workflow.py` + Docker).

Attempting to force both workflows into a single monolithic entry point created unnecessary coupling between local USB drivers and cloud REST APIs.

## Decision
Architect the codebase with **dual distinct entry points**:
1. **Edge Industrial Mode (`main.py`)**:
   - Manages industrial camera capture, local hardware inference (`VisionEngine`), `RelayController`, SQLite database with WAL, and WebSockets.
   - Designed for desktop deployment with Tauri.
2. **Cloud & Workflow Mode (`workflow_app/app.py` & `run_workflow.py`)**:
   - Manages batch image evaluations against Roboflow Workflow APIs, provides web-based file upload endpoints (`/api/upload`), and serves a responsive static web dashboard.
   - Containerized via `Dockerfile` (listening on port 7860) and shareable via `share_online.sh` (localtunnel).

## Alternatives Considered

### 1. Unified Single Application
- **Pros**: Single entry point command.
- **Cons**: Cloud container would fail to start if USB camera or relay dependencies failed to initialize; heavy local dependencies (OpenVINO, CoreML) would bloat cloud Docker images; unnecessary security surface on edge hardware.
- **Rejected**: Dual modes provide cleaner separation of concerns and simpler containerization.

### 2. Splitting into Two Independent Repositories
- **Pros**: Completely isolated codebases.
- **Cons**: Code duplication for shared utilities, schemas, and defect class definitions; difficult to synchronize dataset changes.
- **Rejected**: Maintaining a modular monorepo allows sharing core algorithms while keeping deployment targets lightweight.

## Consequences
- **Positive**:
  - Cloud Docker image runs seamlessly on Hugging Face Spaces or cloud VMs without hardware errors.
  - Edge sorting installation runs with zero cloud or internet dependencies.
  - Operators can use the web evaluator (`workflow_app/`) for offline accuracy audits and image inspections.
- **Negative / Trade-offs**:
  - Developers must be aware of which entry point to launch depending on their task.
