# Walkthrough: Phase 6 — Handover & Acceptance

This walkthrough documents the handover package and final deliverables for the **Automated Durian Classification System**.

---

## 1. Handover Package Deliverables

All deliverables requested for system handover and final acceptance are fully written and committed:
- **System Architecture Document**: Compiled [architecture.md](file:///Users/iminluv/Documents/New%20project/docs/architecture.md) detailing backend modules, SQLite WAL configuration, periodic backup scheduling, and WebSocket message schemas.
- **Operator Guides (Vietnamese & English)**:
  - English Operator Guide: [user_guide_en.md](file:///Users/iminluv/Documents/New%20project/docs/user_guide_en.md)
  - Vietnamese Operator Guide: [user_guide_vi.md](file:///Users/iminluv/Documents/New%20project/docs/user_guide_vi.md)

---

## 2. Final System Features Recap

1. **VisionEngine**: Runs platform-specific optimal backends (CoreML on Apple Silicon/macOS, OpenVINO on Windows/Intel) with universal ONNX fallback.
2. **RuleEngine**: Evaluates defect detections on dynamic HSL boundaries and counts using customizable, hot-reloadable JSON benchmark profiles.
3. **Database**: SQLite database running in write-ahead logging (WAL) mode with background auto-backups every 15 minutes.
4. **Relay Controller**: Drives industrial sorting actuators via USB HID packets with automatic mock fallbacks on dev machines.
5. **FastAPI & Tauri App Shell**: Streams live camera video (MJPEG over WebSockets) and delivers real-time grading events to a premium glassmorphic dark-mode frontend.
6. **Retraining & OTA Updates**: Employs Celery + Redis worker queues to retrain models, compile weights, and prompt operators for approval.
7. **Report Writers**: Generates batch summaries, detailed histories, and charts in Excel (.xlsx) and PDF (.pdf) formats.
