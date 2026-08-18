# ADR-001: Split-Process Architecture using Tauri Desktop Shell and FastAPI Backend

## Status
Accepted

## Date
2026-05-20

## Context
The industrial durian classification system requires real-time computer vision processing (10–30 FPS frame capture, deep learning inference, frame annotation, and USB hardware relay triggering) alongside a responsive, modern desktop operator interface.

Key constraints & requirements:
- **Low Memory & CPU Footprint**: Edge computers in packing houses often have limited RAM (4–8 GB) and must maintain high CPU headroom for inference.
- **Asynchronous Non-Blocking Pipeline**: Computer vision frame capture and inference must never freeze or drop frames due to UI rendering or user interactions.
- **Cross-Platform Compatibility**: Must run natively on both macOS (Apple Silicon dev/testing environments) and Windows/Linux industrial edge PCs.
- **Direct Hardware Access**: Needs direct OS-level access to USB HID Relays (VID `0x16c0`, PID `0x05df`) and USB/RTSP camera drivers.

## Decision
Adopt a **split-process architecture**:
1. **Frontend**: A **Tauri** desktop application (Rust shell with lightweight HTML5/Vanilla JS/CSS frontend) providing the operator interface.
2. **Backend**: A dedicated local **FastAPI** web server running Python 3.11 for computer vision, database logging, and hardware control.
3. **Inter-Process Communication (IPC)**: Local WebSockets (`ws://127.0.0.1:8000/ws/live` for 10 FPS Base64 JPEG video streaming and `ws://127.0.0.1:8000/ws/events` for real-time sorting notifications) plus HTTP REST endpoints for configuration, batch control, and report generation.

## Alternatives Considered

### 1. Monolithic Electron Application
- **Pros**: Mature ecosystem, full Node.js ecosystem, easy cross-platform packaging.
- **Cons**: High baseline memory consumption (>250 MB RAM per instance), bundled Chromium overhead, complex integration with Python vision and deep learning wheels.
- **Rejected**: Too heavy for industrial edge hardware with constrained memory.

### 2. Pure Python Desktop GUI (PyQt / PySide / Tkinter)
- **Pros**: Single-language codebase, direct Python object passing.
- **Cons**: Difficult to design modern glassmorphic responsive dashboards, UI rendering on Python's GIL can introduce micro-stutters during heavy image tensor operations, brittle cross-platform styling.
- **Rejected**: Inferior user experience and increased risk of GIL contention between inference and UI loops.

### 3. Pure Web Browser Interface
- **Pros**: Zero installation on client machines.
- **Cons**: Requires operator to manually open a browser, cannot package native tray icons, window management, or automatic backend lifecycle management as a native desktop binary.
- **Rejected**: Industrial operators require a one-click desktop executable with managed lifecycle.

## Consequences
- **Positive**:
  - Memory consumption of the Tauri desktop shell is under 40 MB RAM.
  - Complete isolation between UI thread and camera inference loop prevents frame drops.
  - Native binary packaging with Tauri sidecar (`bin/durian-backend`) allows one-click launcher behavior.
  - Backend can be independently tested or deployed in containerized cloud environments.
- **Negative / Trade-offs**:
  - Requires maintaining WebSockets and REST API contracts between frontend and backend.
  - Development requires both Rust/Node tooling and Python virtual environments.
