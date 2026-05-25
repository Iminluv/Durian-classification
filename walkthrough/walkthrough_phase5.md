# Walkthrough: Phase 5 — Pilot at Customer Site

This walkthrough documents the setup, execution, and verification steps for **Phase 5: Pilot at Customer Site**.

---

## 1. Mock Simulation & Edge Testing Setup

To enable shadow testing on developer setups and edge computers without camera hardware or permission configurations, we developed custom mock components:
- **Mock Camera Capture Fallback**: Configured [capture.py](file:///Users/iminluv/Documents/New%20project/core/capture.py) with a `MockVideoCapture` class. If the system fails to initialize a physical USB/RTSP camera, it automatically falls back to generating a moving synthetic durian frame. The synthetic frame generates periodic defect items (fungus, cracks, spots) to trigger the vision and grading rule engines.
- **Shadow Mode Simulator**: Programmed [simulate_shadow_mode.py](file:///Users/iminluv/Documents/New%20project/simulate_shadow_mode.py) which simulates a real-time conveyor belt session. It passes 20 fruits sequentially, runs the grading rules, commits logs to SQLite in WAL mode, activates mock diverters, and prints statistics.

---

## 2. Running a Shadow Mode Test

To run the conveyor belt simulator:
1. Activate your virtual environment and run:
   ```bash
   python simulate_shadow_mode.py
   ```
2. The script will initialize a unique batch session `SIM_SHADOW_<timestamp>`, run the conveyor loops, log detections, and output a summary report.

### Sample Execution Output:
```
======================================================================
 SHADOW MODE SIMULATOR - BATCH ID: SIM_SHADOW_20260525_181145
======================================================================

[Fruit #01/20] Passing conveyor sensor...
  Simulated defects: None (Clean)
  System Grade Decision: [GRADE A]

[Fruit #02/20] Passing conveyor sensor...
  Simulated defects: fungus
  System Grade Decision: [GRADE reject]
  Decision Reasons: Force Reject: fungus

...

======================================================================
 SIMULATION SHADOW MODE REPORT SUMMARY
======================================================================
  Batch Session ID: SIM_SHADOW_20260525_181145
  Total Fruits Processed: 20
  Grade A Count:   11 (55.0%)
  Grade B Count:   4 (20.0%)
  Grade C Count:   2 (10.0%)
  Reject Count:    3 (15.0%)
======================================================================
```

---

## 3. Reporting Integrations Verified

Once the shadow batch completes, Excel and PDF reports can be immediately fetched and reviewed using these endpoints:
- **Excel Report**: `GET http://127.0.0.1:8000/api/reports/SIM_SHADOW_<timestamp>/excel`
- **PDF Report**: `GET http://127.0.0.1:8000/api/reports/SIM_SHADOW_<timestamp>/pdf`
