# Roboflow Workflow Evaluation Report

**Project:** Automated Durian Classification System
**Date:** May 26, 2026
**Dataset:** `durian/test/images` — 138 annotated images
**Workflow:** Roboflow Cloud Inference (`phongs-workspace-kigpq`)

---

## 1. Executive Summary

The Roboflow-hosted durian defect detection workflow was evaluated against the full test set of **138 labeled images** across 4 defect classes. The workflow achieved an overall **94.20% hit rate** (130/138 images correctly detected), with an average inference runtime of **1.070 seconds per image**.

| Metric | Value |
|---|---|
| Total Images Evaluated | 138 |
| Total Hits | 130 |
| Total Misses | 8 |
| **Overall Hit Rate** | **94.20%** |
| Average Runtime | 1.070s |
| Min Runtime | 0.581s |
| Max Runtime | 14.548s (cold start) |

---

## 2. Per-Class Results

### 2.1 Hit Rate by Defect Class

| Class | Images Tested | Hits | Misses | Hit Rate |
|---|---|---|---|---|
| `crack` | 51 | 51 | 0 | **100.0%** ✅ |
| `thorn_split` | 19 | 18 | 1 | **94.7%** ✅ |
| `fungus` | 48 | 44 | 4 | **91.7%** ✅ |
| `dark_spot` | 31 | 27 | 4 | **87.1%** ⚠️ |

> **Note:** Some images have multiple expected classes (e.g., `dark_spot` + `fungus`), so per-class counts sum to more than 138.

### 2.2 Confidence Distribution by Class

| Class | Predictions Count | Avg Confidence | Min Confidence | Max Confidence |
|---|---|---|---|---|
| `dark_spot` | 22 | 0.865 | 0.512 | 0.969 |
| `crack` | 86 | 0.832 | 0.436 | 0.967 |
| `thorn_split` | 58 | 0.782 | 0.438 | 0.956 |
| `fungus` | 62 | 0.721 | 0.255 | 0.954 |

**Key observation:** `fungus` has the lowest average confidence (0.721) and the widest confidence range, indicating the model is less certain when detecting fungus — some predictions have confidence as low as 0.255.

---

## 3. Multi-Class Image Performance

Images with more than one expected defect class are harder to evaluate because the workflow must detect **all** classes to count as a hit.

| Metric | Value |
|---|---|
| Multi-class images | 11 |
| Hits | 9 |
| Misses | 2 |
| **Hit Rate** | **81.8%** |

---

## 4. Missed Images — Detailed Analysis

8 images failed detection. Below is the breakdown:

### 4.1 Complete Detection Failures (No Predictions)

These images returned **zero predictions** from the workflow:

| # | Image | Expected Classes |
|---|---|---|
| 1 | `images-2-_jpg.rf.45209127...` | `dark_spot`, `fungus` |
| 2 | `afruitrot1a_jpg.rf.81fe12e...` | `fungus` |
| 3 | `rotated270_fugus_durian56_jpeg.rf.c31d80...` | `fungus` |
| 4 | `tinh-trang-be-gai-tren-trai-sau-rieng-01-scaled__equalize_cr...` | `thorn_split` |
| 5 | `2014__blur_bright_png_png.rf.5d5478e...` | `dark_spot` |

**Root Cause Hypothesis:** These images may have unusual lighting (blur + brightness augmentation), extreme rotation (270°), or low-contrast defect regions that fall below the model's detection threshold.

### 4.2 Wrong Class Predicted (Misclassification)

These images had predictions, but for the **wrong defect class**:

| # | Image | Expected | Predicted | Confidence |
|---|---|---|---|---|
| 6 | `AdobeStock_267183627...` | `crack`, `fungus` | `crack` only (0.65) | Fungus missed |
| 7 | `6049__contrast_down...` | `dark_spot` | `thorn_split` (0.93) | High-confidence misclassification |
| 8 | `6044__gamma_flip...` | `dark_spot` | `thorn_split` (0.86) | High-confidence misclassification |

**Key Concern:** Images #7 and #8 show the model confidently predicting `thorn_split` (0.93, 0.86) when the ground truth is `dark_spot`. This suggests **class confusion between `dark_spot` and `thorn_split`** in certain augmentation scenarios (contrast-down, gamma-flip).

---

## 5. Failure Pattern Analysis

| Failure Type | Count | Affected Classes | Pattern |
|---|---|---|---|
| Zero predictions | 5 | `fungus` (2), `dark_spot` (2), `thorn_split` (1) | Heavy augmentation (blur, brightness, equalize) |
| Partial hit (multi-class) | 1 | `fungus` missed | Only `crack` detected in multi-defect image |
| Misclassification | 2 | `dark_spot` → `thorn_split` | Contrast/gamma transformations |
| **Total** | **8** | | |

### Observations

1. **`crack` class is perfect** — 100% hit rate, 51/51 images detected. The model has strong feature representation for cracks.
2. **`dark_spot` is the weakest at 87.1%** — fails in low-contrast or gamma-adjusted images, sometimes confused with `thorn_split`.
3. **`fungus` detection at 91.7%** — generally strong, but fails on rotated images and those with heavy augmentation artifacts.
4. **`thorn_split` at 94.7%** — only 1 miss on an equalize-cropped image.
5. **Cold start penalty** — the first API call took 14.5 seconds; subsequent calls averaged ~1.0 second.

---

## 6. Runtime Performance

| Metric | Value |
|---|---|
| Average Runtime | 1.070 seconds |
| Median Runtime (est.) | ~0.85 seconds |
| Min Runtime | 0.581 seconds |
| Max Runtime | 14.548 seconds |
| Total Evaluation Time | ~147.7 seconds |

> **Note:** These timings reflect cloud API latency (network round-trip + inference). The production on-device OpenVINO runtime target is **<200ms per frame**, which is ~5× faster than the cloud average.

---

## 7. KPI Gate Assessment

| KPI | Target | Actual | Status |
|---|---|---|---|
| Overall Hit Rate | ≥ 85% | **94.20%** | ✅ PASSED |
| Recall — `crack` | ≥ 85% | **100.0%** | ✅ PASSED |
| Recall — `fungus` | ≥ 85% | **91.7%** | ✅ PASSED |
| Recall — `dark_spot` | ≥ 85% | **87.1%** | ✅ PASSED (marginal) |
| Recall — `thorn_split` | ≥ 85% | **94.7%** | ✅ PASSED |
| Inference Latency | < 200ms | 1,070ms (cloud) | ⚠️ N/A (cloud only) |

> All accuracy KPIs are met. The `dark_spot` class passes at 87.1% but is the closest to the threshold — targeted improvement recommended.

---

## 8. Recommendations

### Short-Term (Immediate)

1. **Improve `dark_spot` training data** — add more low-contrast and gamma-adjusted examples to reduce confusion with `thorn_split`
2. **Review ground truth labels** for the 2 misclassified images — verify if `dark_spot` vs `thorn_split` labeling is correct in the ground truth
3. **Add targeted augmentation** for `fungus` class — more rotation variants (270°) and blur combinations

### Medium-Term

4. **Lower confidence threshold for `fungus`** — currently at 0.40, consider lowering to 0.35 to catch borderline cases (avg confidence is 0.721, but min is 0.255)
5. **Run on-device evaluation** — replicate this test using the exported OpenVINO model to validate <200ms latency on Intel i5
6. **Add confusion matrix tracking** — log not just hits/misses but also which wrong class was predicted for systematic error analysis

### Long-Term

7. **Continuous evaluation pipeline** — automate this evaluation as part of the retrain cycle to track accuracy trends across model versions
8. **A/B testing** — compare cloud workflow vs on-device model accuracy on the same test set before production cutover

---

*Report generated from `run_workflow.py` execution on May 26, 2026*
*Source data: [evaluation_results.json](evaluation_results.json) (138 images)*
