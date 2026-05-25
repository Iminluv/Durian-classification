# Automated Durian Classification System — English Operator Guide

This guide describes how to operate the Durian Classification desktop application.

---

## 1. System Startup

1. **Verify Connections**:
   - Ensure the industrial camera (USB/RTSP) is powered and connected.
   - Verify the USB Relay Controller is plugged into a USB port on the edge computer.
2. **Launch Application**:
   - Locate the application shortcut on the Desktop.
   - Launch the Tauri desktop app. The backend FastAPI service will start automatically in the background as a sidecar process.

---

## 2. Dashboard Widgets

The main dashboard is divided into three functional widgets:
- **Live Feed Canvas**: Displays real-time camera video. Detected defects (`crack`, `dark_spot`, `fungus`, `thorn_split`, `reject`) are color-coded with bounding boxes drawn directly over the feed.
- **Current Grade Badge**: Shows a large letter `A`, `B`, `C`, or `REJECT` corresponding to the graded quality of the fruit currently under the camera.
  - A red warning banner flashes on the screen if a fruit is categorized as a Reject or Fungus.
- **Defect Progress Bars**: Shows real-time confidence scores for the various defect types.
- **Grade Counters & Event Log**: Tracks processed counts and list details of recent sorting events.

---

## 3. Batch Management

To run a sorting session:
1. Navigate to the **Batches** tab in the sidebar.
2. Enter a unique **Batch ID** (e.g. `BATCH_V1_001`) and the **Operator ID**.
3. Choose the active **Grading Benchmark** from the dropdown.
4. Click **Start Batch** to start recording log data.
5. Click **Stop Batch** when the sorting session is complete. Detections will only be logged to the local SQLite database when a batch is active.

---

## 4. Benchmark Profile Configurations

You can modify how defects map to grades:
1. Navigate to the **Benchmarks** tab.
2. Select an existing profile to edit, or click **New Benchmark**.
3. For each defect:
   - **Max A, B, C**: Sets the maximum number of times this defect can appear on a fruit for it to qualify for that grade.
   - **Max Area Ratio**: Sets the maximum percentage of the fruit's surface area this defect can cover.
   - **Force Reject**: Check this box to force an immediate Reject grade if this defect is found.
4. Click **Save** to apply changes. Changes are updated immediately at runtime.

---

## 5. History & Reports

1. Navigate to the **History & Reports** tab.
2. Search for the target **Batch ID** using the search bar.
3. The paginated table displays timestamp, final grade, defects found, and confidence logs.
4. Click **Download Excel** or **Download PDF** to export batch statistics.

---

## 6. OTA Model Updates

If a new, retrained model is available, a notification will appear under the **Settings** tab.
- Metrics comparing the new model and current model (Recall, mAP@50, Latency) will be shown side-by-side.
- Click **Approve Update** to deploy the new weights immediately.
- Click **Reject Update** to keep the current model and clear the pending update.
