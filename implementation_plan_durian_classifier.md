# Implementation Plan — Automated Durian Classification System
**Project:** Starter Package — Edge-based Durian Grading Software
**Total Duration:** ~16–18 weeks
**Target Platform:** Offline-first Edge (Intel i5, CPU-only, no GPU)

---

## Tech Stack Summary

| Layer | Technology | Purpose |
|---|---|---|
| Image capture | OpenCV (Python) | Camera feed ingestion (USB/RTSP) |
| Annotation | Label Studio (self-hosted) | Defect region labeling at localhost |
| Augmentation | Albumentations | Realistic on-site augmentation |
| Dataset versioning | DVC | Track dataset changes across retrains |
| Training framework | PyTorch | Model training backbone |
| Model architecture | YOLOv26n | Defect detection + localization |
| Inference runtime | OpenVINO (mandatory) | CPU-optimized inference on Intel i5 |
| Inference fallback | ONNX Runtime | Used only if OpenVINO unavailable |
| Grading logic | Rule engine (Python) | Maps defect detections → A/B/C/Reject |
| Experiment tracking | MLflow (self-hosted) | Track metrics across v1→v2→v3 |
| Retrain queue | Celery + Redis | Async retrain triggered from labeling tool |
| Local database | SQLite | Batch history, images, event logs |
| Application layer | Python (FastAPI or service) | Vision engine, rule engine, relay output |
| Frontend / UI | HTML + JS (localhost) | Operator UI + labeling tool |
| Report export | openpyxl + ReportLab | Excel and PDF report generation |
| OTA updates | Sync agent (rsync/HTTP) | Push new model when internet available |

---

## System Logic Overview

The model and grading are deliberately separated into two layers:

```
YOLOv26n (Detection layer)
  └── Detects and localizes visible defects on the fruit surface
  └── Outputs: [defect_type, bounding_box, confidence] per detected region
        │
        ▼
Rule Engine (Grading layer)
  └── Receives defect list from model
  └── Applies configurable thresholds per defect type/count/area
  └── Outputs final grade: A / B / C / Reject
```

This separation means grading criteria can be updated by the customer (via `rules.json`) without retraining the model.

---

## Defect Classes

The model detects the following visible defect types. Final list to be confirmed with customer QC staff before annotation begins.

| Class label | Description | Typical grade impact |
|---|---|---|
| `crack` | Shell crack or split | Likely Reject |
| `dark_spot` | Discoloration or rot patch | B or C depending on area |
| `bruise` | Physical impact damage | B or C depending on severity |
| `mold` | Fungal growth visible on shell | Reject |
| `missing_thorn` | Large bald patch on shell | C or Reject |
| `reject` | Hard-override: fruit is unconditionally rejected | Always Reject |

> **Note:** `reject` is a standalone detection class for cases where the overall fruit is disqualified regardless of individual defect scoring (e.g. severely deformed shape, extreme rot). The rule engine treats any `reject` detection as an immediate override.

---

## Phase 1 — Data Collection & Preparation
**Duration:** 2–3 weeks | **Goal:** Labeled defect dataset ≥500 images/defect class ready for training

### 1.1 Camera & Capture Setup
- Install OpenCV capture script on the edge device targeting the conveyor belt camera (USB UVC or RTSP IP camera)
- Configure frame extraction to trigger on object presence (motion threshold or IR sensor signal)
- Save raw frames as JPEG (80% quality) to `/data/raw/<date>/<batch_id>/`
- Target capture rate: 2–5 frames per fruit at different belt positions and lighting angles

### 1.2 Annotation Workflow
- Deploy **Label Studio** at `localhost:8080` on the edge machine
- Create a project with **bounding box** template — annotators draw boxes around each defect region and assign the defect class label
- Annotation protocol:
  1. Import raw frames in batches of 200
  2. Each image annotated by 1 primary annotator + 1 reviewer
  3. Disagreements escalated to customer QC staff
  4. Pay special attention to `reject` and `mold` — these must have high annotation consistency given their high recall priority
- Export format: **YOLO TXT** (primary) + **COCO JSON** (backup)
- Store annotations in `/data/annotated/v1/`

### 1.3 Augmentation Pipeline
Run **Albumentations** pipeline to expand dataset to ≥3,000 images/defect class:

```python
import albumentations as A

transform = A.Compose([
    A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.8),
    A.HueSaturationValue(hue_shift_limit=10, p=0.5),
    A.MotionBlur(blur_limit=5, p=0.3),          # simulate belt movement
    A.GaussNoise(var_limit=(10, 50), p=0.4),
    A.RandomShadow(p=0.3),                        # simulate warehouse lighting
    A.HorizontalFlip(p=0.5),
    A.ShiftScaleRotate(shift_limit=0.05, scale_limit=0.1, rotate_limit=10, p=0.6),
    A.CLAHE(p=0.3),                               # enhance defect contrast
], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))
```

### 1.4 Dataset Versioning
- Initialize **DVC** repository: `dvc init`
- Track `/data/annotated/` and `/data/augmented/` with DVC
- Push to remote storage (NAS or USB backup drive) after each labeling session
- Tag release: `git tag dataset-v1.0`

### Deliverables
- [ ] Dataset ≥500 labeled images per defect class
- [ ] Augmented dataset ≥3,000 images per defect class
- [ ] `dataset-v1.0` DVC tag committed
- [ ] Written defect class definitions document (signed by customer QC lead)

---

## Phase 2 — Model v1 Training
**Duration:** 2–3 weeks | **Goal:** Model with recall ≥85% on `reject` and `mold` classes on held-out test set

### 2.1 Dataset Split

```
Total: ~18,000 images (3,000 × 6 defect classes)
├── train/   70%  ~12,600 images
├── val/     15%   ~2,700 images
└── test/    15%   ~2,700 images   ← held out, never seen during training
```

### 2.2 Model: YOLOv26n

YOLOv26n is used as the detection backbone. It performs a single forward pass to output defect bounding boxes, defect class labels, and confidence scores per detected region. The nano variant is selected for CPU inference compatibility on Intel i5 Gen 10+ without GPU.

```yaml
# durian.yaml
path: /data/augmented
train: train
val: val
test: test
nc: 6
names: ['crack', 'dark_spot', 'bruise', 'mold', 'missing_thorn', 'reject']
```

### 2.3 High-Recall Training Strategy

Since the priority is **catching every bad fruit** (high recall on `reject` and `mold`), the training pipeline applies the following adjustments:

**a) Class weights — penalize missed detections on critical classes**
```python
# Higher weight on reject and mold → model pays more attention to these
class_weights = {
    'crack':         1.0,
    'dark_spot':     1.0,
    'bruise':        1.0,
    'mold':          2.5,   # severe consequence if missed
    'missing_thorn': 1.0,
    'reject':        3.0,   # highest priority — never miss
}
```

**b) Lower confidence threshold for `reject` and `mold` at inference**
```python
# Per-class threshold overrides at inference time
CONFIDENCE_THRESHOLDS = {
    'crack':         0.60,
    'dark_spot':     0.60,
    'bruise':        0.60,
    'mold':          0.40,   # accept more false positives to catch all mold
    'missing_thorn': 0.55,
    'reject':        0.35,   # lowest threshold — flag aggressively
}
```

**c) NMS IoU tuning**
- Use lower NMS IoU threshold (0.40) to avoid suppressing overlapping defect boxes on densely defective fruit

### 2.4 Training Command

```bash
yolo train \
  model=yolov26n.pt \
  data=durian.yaml \
  epochs=120 \
  imgsz=640 \
  batch=16 \
  patience=25 \
  device=cpu \
  project=runs/train \
  name=durian_v1
```

### 2.5 Experiment Tracking (MLflow)

```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("durian-defect-detector")

with mlflow.start_run(run_name="yolov26n-v1"):
    mlflow.log_params({"model": "yolov26n", "epochs": 120, "imgsz": 640})
    mlflow.log_metrics({
        "mAP50":          map50,
        "recall_reject":  recall_reject,   # primary KPI
        "recall_mold":    recall_mold,     # secondary KPI
        "precision_all":  precision_all,
    })
    mlflow.log_artifact("runs/train/durian_v1/weights/best.pt")
```

### 2.6 Export to OpenVINO (Mandatory)

OpenVINO is the required inference runtime. All model exports target OpenVINO IR format for optimized CPU execution on Intel hardware.

```python
from ultralytics import YOLO

model = YOLO("runs/train/durian_v1/weights/best.pt")

# Export to OpenVINO IR (mandatory)
model.export(format="openvino", imgsz=640, half=False)
# Output: durian_v1_openvino_model/
#   ├── best.xml
#   └── best.bin
```

Fallback export to ONNX (only used if OpenVINO runtime is unavailable on target hardware):
```python
model.export(format="onnx", imgsz=640, opset=17, simplify=True)
```

### 2.7 Evaluation

Evaluate on held-out test set. KPI gates for proceeding to Phase 3:

| Metric | Target |
|---|---|
| Recall — `reject` class | ≥ 85% |
| Recall — `mold` class | ≥ 85% |
| mAP@50 overall | ≥ 70% |
| Inference latency (OpenVINO, i5) | < 200ms/frame |

> **Note:** Overall precision is a secondary metric. A higher false positive rate on `reject` is acceptable — the cost of wrongly flagging a good fruit is lower than the cost of passing a defective one.

If KPI not met: collect 200+ additional images for under-performing defect classes, re-augment, retrain from last checkpoint.

### Deliverables
- [ ] `best.xml` + `best.bin` — YOLOv26n OpenVINO IR model v1 exported
- [ ] MLflow run logged with recall metrics as primary KPI
- [ ] Evaluation report (`model_v1_evaluation.pdf`)
- [ ] Recall ≥85% on `reject` and `mold` on test set ✓

---

## Phase 3 — Core Application Development
**Duration:** 4–5 weeks | **Goal:** Working defect detection pipeline with rule-based grading and relay output

### 3.1 System Architecture

```
Camera (USB/RTSP)
       │
       ▼
 Frame Capture (OpenCV)
       │
       ▼
 Vision Engine — YOLOv26n via OpenVINO
   └── Outputs: list of {defect_type, bbox, confidence}
       │
       ▼
 Rule Engine (configurable thresholds)
   └── Count defects by type
   └── Compute defect area ratio
   └── Apply grade mapping rules from rules.json
   └── Any `reject` detection → immediate Reject override
   └── Final grade: A / B / C / Reject
       │
   ┌───┴────────────────┐
   ▼                    ▼
Relay Output       Local Database
(GPIO/USB relay)   (SQLite)
  └── trigger        └── log detections,
      conveyor           grade, image path,
      diverter           batch metadata
```

### 3.2 Vision Engine

```python
# core/vision_engine.py
from openvino.runtime import Core
import cv2, numpy as np

class VisionEngine:
    def __init__(self, model_xml: str):
        core = Core()
        model = core.read_model(model=model_xml)
        self.compiled = core.compile_model(model=model, device_name="CPU")
        self.infer_req = self.compiled.create_infer_request()

    def infer(self, frame: np.ndarray) -> list[dict]:
        blob = self._preprocess(frame)   # resize 640x640, normalize
        self.infer_req.infer(inputs={0: blob})
        raw = self.infer_req.get_output_tensor(0).data
        return self._postprocess(raw)    # returns list of {type, bbox, confidence}

    def _postprocess(self, raw) -> list[dict]:
        detections = []
        for det in raw[0]:
            conf = float(det[4])
            cls  = int(det[5])
            name = CLASS_NAMES[cls]
            if conf >= CONFIDENCE_THRESHOLDS[name]:
                detections.append({
                    "type":       name,
                    "confidence": conf,
                    "bbox":       det[:4].tolist()
                })
        return detections
```

### 3.3 Rule Engine

```python
# core/rule_engine.py
import json

class RuleEngine:
    def __init__(self, config_path: str = "config/rules.json"):
        with open(config_path) as f:
            self.rules = json.load(f)

    def grade(self, detections: list[dict], frame_area: int) -> str:
        # Immediate reject override
        if any(d["type"] == "reject" for d in detections):
            return "reject"
        if any(d["type"] == "mold" for d in detections):
            return "reject"

        defect_area_ratio = sum(self._bbox_area(d["bbox"]) for d in detections) / frame_area
        defect_count      = len(detections)
        critical_types    = {d["type"] for d in detections}

        # Apply rules from config
        for rule in self.rules["grade_rules"]:
            if (defect_count      <= rule["max_defect_count"] and
                defect_area_ratio <= rule["max_area_ratio"]   and
                not critical_types.intersection(rule["forbidden_types"])):
                return rule["grade"]

        return "reject"
```

```json
// config/rules.json
{
  "grade_rules": [
    { "grade": "A", "max_defect_count": 0, "max_area_ratio": 0.00, "forbidden_types": [] },
    { "grade": "B", "max_defect_count": 1, "max_area_ratio": 0.03, "forbidden_types": ["crack", "mold"] },
    { "grade": "C", "max_defect_count": 3, "max_area_ratio": 0.08, "forbidden_types": ["mold"] }
  ]
}
```

### 3.4 SQLite Schema

```sql
CREATE TABLE detections (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
    batch_id      TEXT NOT NULL,
    final_grade   TEXT NOT NULL,
    defect_types  TEXT,               -- JSON array of detected defect labels
    defect_count  INTEGER DEFAULT 0,
    confidence    REAL,
    image_path    TEXT,
    overridden    BOOLEAN DEFAULT 0,
    operator_id   TEXT
);

CREATE TABLE batches (
    batch_id      TEXT PRIMARY KEY,
    start_time    DATETIME,
    end_time      DATETIME,
    total_count   INTEGER DEFAULT 0,
    grade_a       INTEGER DEFAULT 0,
    grade_b       INTEGER DEFAULT 0,
    grade_c       INTEGER DEFAULT 0,
    reject        INTEGER DEFAULT 0
);
```

### 3.5 Relay Output

```python
# core/relay_controller.py
import hid, time

class RelayController:
    GRADE_CHANNEL = {"A": 1, "B": 2, "C": 3, "reject": 4}

    def __init__(self, vendor_id=0x16c0, product_id=0x05df):
        self.device = hid.open(vendor_id, product_id)

    def trigger(self, grade: str, pulse_ms: int = 200):
        ch = self.GRADE_CHANNEL[grade]
        self.device.write([0x00, ch, 0xFF])
        time.sleep(pulse_ms / 1000)
        self.device.write([0x00, ch, 0x00])
```

### 3.6 Labeling Tool & Retrain Pipeline

- Label Studio served at `localhost:8080`
- Operator marks missed defects or incorrect detections → corrections queued
- When new labeled samples ≥200, retrain task auto-triggered via Celery:

```python
# tasks/retrain.py
from celery import Celery

app = Celery("retrain", broker="redis://localhost:6379/0")

@app.task
def trigger_retrain(new_data_path: str):
    merge_datasets(new_data_path, "/data/annotated/")
    run_augmentation()
    train_model()           # YOLOv26n fine-tune from last checkpoint
    export_to_openvino()    # mandatory export format
    validate_kpi()          # only swap if recall_reject >= current model
    deploy_model_ota()
```

### Deliverables
- [ ] Vision engine running at <200ms/frame via OpenVINO on i5
- [ ] Rule engine with configurable thresholds (`rules.json`)
- [ ] SQLite DB logging all detections with no data loss on power cut
- [ ] Relay output triggering conveyor diverter correctly per grade
- [ ] Labeling tool accessible at localhost
- [ ] Celery retrain pipeline end-to-end tested

---

## Phase 4 — UI & Reporting
**Duration:** 2 weeks | **Goal:** Operator UI and automated report generation

### 4.1 Operator Dashboard

Real-time web UI served at `localhost:3000`:

| Component | Description |
|---|---|
| Live feed panel | Camera frame with defect bounding boxes overlaid (color-coded by defect type) |
| Grade display | Large A/B/C/Reject label for current fruit |
| Defect list | List of detected defect types + confidence for current fruit |
| Grade counters | Running count of A/B/C/Reject for current batch |
| Alert banner | Red banner on any `reject` or `mold` detection |
| Batch controls | Start/stop/pause batch, enter batch ID |

### 4.2 Report Generation

**Excel (openpyxl):**
```python
from openpyxl import Workbook

def export_excel(batch_id: str, output_path: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "Batch Summary"
    # Per-fruit rows: timestamp, grade, defect_types, confidence
    # Summary sheet: grade distribution, defect frequency chart
    wb.save(output_path)
```

**PDF (ReportLab):**
```python
from reportlab.platypus import SimpleDocTemplate, Table

def export_pdf(batch_id: str, output_path: str):
    doc = SimpleDocTemplate(output_path)
    # Grade summary table, defect breakdown, batch metadata, timestamp
    doc.build(elements)
```

### Deliverables
- [ ] Operator UI running stably with defect bounding box overlay
- [ ] Auto-export Excel report per batch (triggered on batch close)
- [ ] Auto-export PDF report per batch
- [ ] User guide delivered

---

## Phase 5 — Pilot at Customer Site
**Duration:** 2–3 weeks | **Goal:** Real-world validation, recall ≥88% on `reject` on live conveyor

### 5.1 Hardware Setup
- Install edge device (mini PC) at customer facility
- Mount camera above conveyor at correct angle and distance
- Wire relay to physical diverter mechanism
- Confirm OpenVINO runtime installed and validated on target CPU
- Test UPS failover — ensure SQLite data integrity on power cut

### 5.2 Shadow Mode (Week 1)
- System runs in parallel with human workers — relay is **disabled**
- Compare system grades vs human grades for the same fruits
- Track false negatives closely: any `reject` fruit passed by the system is a critical miss
- Collect all disagreements as new labeled data for retraining

### 5.3 Live Mode (Week 2–3)
- Enable relay output — system controls the conveyor diverter
- Human supervisor spot-checks every 30 minutes with focus on `reject` lane accuracy
- Supervisor uses operator UI to mark missed defects → fed back to labeling tool
- Monitor: latency histogram, recall on `reject`, per-shift false negative count

### 5.4 Threshold Calibration
Adjust rule engine and confidence thresholds based on pilot data — no retraining required:
- If too many good fruits flagged as Reject: raise `reject` confidence threshold slightly
- If defective fruits passing as Grade B: lower `dark_spot` or `bruise` threshold, or tighten `rules.json` area ratio
- All adjustments in `config/rules.json` and `CONFIDENCE_THRESHOLDS`

### Deliverables
- [ ] Shadow mode report: false negative count on `reject` class
- [ ] Live mode running stably ≥5 consecutive shifts
- [ ] Recall on `reject` ≥88% on live conveyor (KPI gate for go-live)
- [ ] Labeled disagreement dataset collected (feeds Phase 6)

---

## Phase 6 — Fine-Tuning & Acceptance
**Duration:** 1–2 weeks | **Goal:** Model v2 accepted, handover complete

### 6.1 Model v2 Retrain
- Merge Phase 5 disagreement data with original dataset
- Fine-tune YOLOv26n from last checkpoint (not from scratch)
- Validate on both original test set and new live-condition test set
- Export to OpenVINO IR, push via OTA update

### 6.2 KPI Gate

| Milestone | When | Primary KPI | Secondary KPI |
|---|---|---|---|
| Model v1 (Pilot entry) | End of Week 8 | Recall `reject` ≥ 85% | mAP@50 ≥ 70% |
| Model v2 (Go-live) | End of Week 14 | Recall `reject` ≥ 88% | Latency < 200ms |
| Model v3 (Month 4) | Month 4 | Recall `reject` ≥ 93% | — |

### 6.3 Acceptance Criteria
- [ ] Latency <200ms per fruit at 15 fruits/minute belt speed (OpenVINO runtime)
- [ ] Zero data loss events across 5-shift endurance test
- [ ] Relay response <50ms after grade decision
- [ ] Recall on `reject` class meets v2 KPI on live conveyor
- [ ] Operator can restart system after crash within 2 minutes (documented)
- [ ] All KPI thresholds met and signed off by customer QC lead

### 6.4 Handover Package
- [ ] Full source code in version-controlled repository
- [ ] DVC dataset snapshot (`dataset-v2.0` tag)
- [ ] OpenVINO IR model files (`best.xml` + `best.bin`) + MLflow run export
- [ ] System documentation (architecture, config reference, troubleshooting)
- [ ] Operator training completion certificate

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Insufficient defect images for rare classes (e.g. mold) | High | High | Prioritize mold collection in Phase 1; use Roboflow synthetic data to supplement |
| Recall on `reject` stuck below 85% at v1 | Medium | High | Lower confidence threshold further; increase `reject` class weight to 4.0; collect targeted hard negatives |
| OpenVINO not compatible with target CPU generation | Low | High | Validate OpenVINO on exact hardware before Phase 1; confirm Intel Gen 10+ supports INT8 inference |
| Lighting variation at customer site | High | Medium | Add `RandomShadow` + `CLAHE` in augmentation; install diffuse lighting above camera |
| Latency >200ms after OpenVINO export | Low | Medium | Reduce input resolution to 416×416; enable INT8 quantization via NNCF |
| Rule engine misconfigured → wrong grade mapping | Medium | Medium | Unit-test rule engine against fixed detection sets; customer signs off rules.json before go-live |
| Power cut corrupts SQLite | Low | High | WAL mode enabled; UPS required per spec |

---

## Directory Structure

```
durian-classifier/
├── data/
│   ├── raw/                        # captured frames from camera
│   ├── annotated/                  # labeled defect data (DVC tracked)
│   └── augmented/                  # augmented training set (DVC tracked)
├── models/
│   └── yolov26n_v1/
│       ├── best.pt                 # PyTorch checkpoint
│       ├── best.onnx               # fallback only
│       └── openvino/               # mandatory inference format
│           ├── best.xml
│           └── best.bin
├── core/
│   ├── vision_engine.py            # OpenVINO inference
│   ├── rule_engine.py              # defect → grade mapping
│   ├── relay_controller.py
│   └── database.py
├── tasks/
│   └── retrain.py                  # Celery retrain pipeline
├── ui/
│   ├── operator/                   # real-time dashboard
│   └── labeling/                   # Label Studio config
├── reports/
│   └── templates/
├── config/
│   └── rules.json                  # configurable grade thresholds
├── runs/                           # MLflow + training outputs
├── tests/
├── docs/
│   ├── user_guide.pdf
│   └── architecture.md
├── durian.yaml                     # YOLO dataset config
└── dvc.yaml                        # DVC pipeline
```

---

*Document version: 2.0 — May 2026*
*Based on: Proposal PRO-2026-001 — Starter Package*
