# Automated Durian Classification System — Operator & User Guide

This guide describes how to operate the **Automated Durian Defect Detection and Quality Classification System** desktop and web applications.

---

## 1. System Startup & Preparation

### 1.1 Physical Hardware Checklist
Before launching the application on the packing line:
1. **Industrial Camera**: Ensure the USB or RTSP camera is securely mounted above the conveyor belt with proper illumination (minimum 500 lux, flicker-free LED).
2. **USB Relay Controller**: Verify the 4-channel USB relay module (VID `0x16c0`, PID `0x05df`) is plugged into the edge computer.
3. **Pneumatic Sorting Gates**: Verify the pneumatic air supply is pressurized and sorting gates respond to relay triggers.

### 1.2 Launching the Application
- **Desktop Application**:
  - Locate the **Durian Classifier** icon on the Desktop or launch via terminal:
    ```bash
    cd ui/src-tauri && cargo tauri dev
    ```
  - The backend FastAPI service starts automatically and establishes a WebSocket connection.
- **Web Workflow Runner (Remote Testing / QA)**:
  - If using the browser-based workflow evaluator:
    ```bash
    python workflow_app/app.py
    ```
  - Open `http://127.0.0.1:8000` in your web browser.

---

## 2. Dashboard Widgets & Live Feed

The main dashboard is organized into intuitive, real-time widgets:

```
┌────────────────────────────────────────────────────────┐
│ [LIVE FEED CANVAS]                [CURRENT GRADE]      │
│ Real-time bounding boxes          ┌──────────────────┐ │
│ - crack (Orange)                  │        A         │ │
│ - dark_spot (Brown)               │     (Grade A)    │ │
│ - fungus (Yellow)                 └──────────────────┘ │
│ - thorn_split (Amber)             [CONFIDENCE METRICS] │
│ - reject (Red)                    Crack: 85%  Fungus:0%│
├────────────────────────────────────────────────────────┤
│ [BATCH SUMMARY COUNTERS]                               │
│ Total: 1,420 | Grade A: 920 | Grade B: 340 | C: 120 | R: 40
├────────────────────────────────────────────────────────┤
│ [REAL-TIME EVENT LOG]                                  │
│ 14:22:05 - Fruit #1420 -> Grade A (No defects)         │
│ 14:22:02 - Fruit #1419 -> Grade B (1x dark_spot)       │
└────────────────────────────────────────────────────────┘
```

1. **Live Feed Canvas**: Displays the high-resolution video stream with real-time defect annotations, bounding boxes, and confidence tags.
2. **Current Grade Badge**: Displays a prominent `A`, `B`, `C`, or `REJECT` badge for the fruit currently positioned under the camera.
   - **Flashing Warning**: A prominent red alert flashes if a fruit is flagged as `REJECT` or contaminated with `fungus`.
3. **Defect Confidence Indicators**: Displays real-time confidence scores and area calculations for each detected defect.
4. **Batch Counters**: Tracks aggregate counts for Grade A, Grade B, Grade C, and Reject fruits in the active session.
5. **Real-time Event Log**: Records individual fruit sorting decisions with timestamped defect details.

---

## 3. Batch Management

To record, track, and export sorting session data:

1. Click the **Batches** tab on the navigation sidebar.
2. Enter a unique **Batch ID** (e.g., `BATCH_20260525_A01`).
3. Enter your **Operator ID** (e.g., `OP_JOHN_04`).
4. Select the active **Benchmark Profile** (e.g., `Standard QC v1`).
5. Click **Start Batch**:
   - The status indicator turns green (`ACTIVE`).
   - Every graded fruit is logged to the local SQLite database.
   - Physical relay outputs are energized for each graded fruit.
6. Click **Stop Batch** when the sorting run concludes:
   - Summary statistics are finalized.
   - The database is committed and synchronized.

---

## 4. Benchmark Profile Configurations

Grading standards can be adjusted without retraining the machine learning model:

1. Navigate to the **Benchmarks** tab.
2. Choose an existing profile to edit, or click **New Benchmark**.
3. Configure the parameters for each defect class:
   - **Max A, B, C**: The maximum number of allowable instances of this defect on a single fruit for that grade.
   - **Max Area Ratio**: The maximum percentage of fruit surface area this defect may occupy (e.g., `0.02` = 2%).
   - **Force Reject**: When checked, detecting even a single instance of this defect immediately categorizes the fruit as `REJECT` (e.g., quarantine fungus).
4. Configure **Global Rules**:
   - Total defect count limits across all defect types combined.
   - Total cumulative defect surface area ratio.
5. Click **Save Benchmark**: Changes are hot-reloaded instantly into the running vision pipeline.

---

## 5. History & Report Generation

1. Navigate to the **History & Reports** tab.
2. Search for past sessions by **Batch ID** or date range.
3. Inspect detailed inspection records, including individual fruit timestamps, detected classes, bounding boxes, and confidence levels.
4. Export official compliance documentation:
   - **Download Excel (`.xlsx`)**: Comprehensive multi-tab spreadsheet with summary tables, defect distributions, and raw fruit logs.
   - **Download PDF (`.pdf`)**: Formatted inspection certificate suitable for export clearance and customer audits.

---

## 6. Over-The-Air (OTA) Model Updates

When the background retraining pipeline completes a new model training cycle:

1. A notification banner appears in the **Settings** panel: **"New AI Model Version Available for Review"**.
2. Review the side-by-side KPI comparison:
   - **mAP@50**: Target $\ge 70\%$
   - **Fungus Recall**: Target $\ge 85\%$
   - **Reject Recall**: Target $\ge 85\%$
   - **Inference Latency**: Target $< 100\text{ ms}$ (CoreML) / $< 200\text{ ms}$ (OpenVINO)
3. Actions:
   - **Approve Update**: Instantly loads the new model weights into the live vision engine without stopping the conveyor line.
   - **Reject Update**: Dismisses the candidate weights and retains the currently active model.

---

## 7. Troubleshooting & Operator FAQs

| Issue | Cause | Solution |
|---|---|---|
| **Black video feed** | Camera disconnected or incorrect device index | Check USB cable; verify `"usb_device_id"` in `config/camera.json`. |
| **Relay gates not firing** | USB relay unplugged or wrong port | Verify relay USB connection; check `"relay_mock": false` in `config/app.json`. |
| **No detections logged** | Batch session is not active | Navigate to **Batches** and click **Start Batch**. |
| **High false positive rate** | Benchmark threshold too sensitive | Go to **Benchmarks**, increase confidence thresholds or adjust defect counts. |
