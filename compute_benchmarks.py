"""
compute_benchmarks.py

Computes standard object-detection benchmarks (precision/recall/F1 per class,
mAP@0.5, confusion matrix) from the evaluation_results.json produced by
run_workflow.py.

WHY THIS EXISTS
----------------
run_workflow.py's own "hit rate" metric only checks whether every expected
CLASS was present somewhere in the predictions for an image -- it never
checks whether the predicted BOXES actually line up with the ground-truth
boxes, and it has no way to penalize false positives (extra boxes for
classes that shouldn't be there). This script adds that: it uses IoU
(Intersection over Union) to match predicted boxes to ground-truth boxes,
the same way standard object-detection benchmarks (COCO, PASCAL VOC, and
the mAP50/mAP50-95 numbers YOLO/Ultralytics report) work.

REQUIREMENTS ON THE INPUT DATA
-------------------------------
This script needs evaluation_results.json entries to include "gt_boxes",
"image_width" and "image_height" -- these fields were added to
run_workflow.py's output. If you run this against an OLDER
evaluation_results.json (from before that change), gt_boxes will be
missing/empty and this script will report zero ground truth, which is
wrong -- re-run run_workflow.py first to regenerate the results file.

USAGE
-----
    python compute_benchmarks.py --results evaluation_results.json
    python compute_benchmarks.py --results evaluation_results.json --iou-thresh 0.5
    python compute_benchmarks.py --results evaluation_results.json --group-fungus-dark-spot

The --group-fungus-dark-spot flag reproduces the methodology note already
in your report (fungus and dark_spot predictions are treated as
interchangeable, since fungus growth is a common cause of dark spotting).
Run once WITHOUT the flag (strict, per-class) and once WITH it, and report
both -- the difference between the two numbers is itself informative.

OUTPUT
------
Prints formatted tables to the console, and writes:
  - <out-json> (default: benchmark_results.json): all computed numbers
  - <out-md>   (default: benchmark_results.md): markdown tables, ready to
    paste into evaluation_report.md / the LaTeX report

LIMITATIONS (read before citing numbers in your report)
---------------------------------------------------------
- Precision/Recall/F1 reported here are computed at whatever confidence
  threshold the workflow already applied when it returned predictions --
  this is the "operating point" the deployed system actually uses, not a
  swept threshold curve.
- mAP@0.5 IS threshold-independent (it integrates over confidence), and is
  the number most comparable to standard YOLO/Ultralytics mAP50 output.
- IoU threshold defaults to 0.5 (the conventional choice, matches mAP@0.5).
  Change with --iou-thresh if your teacher wants mAP@0.5:0.95-style
  stricter localization.
- This does NOT compute end-to-end grading accuracy (A/B/C/Reject) -- that
  needs the rule engine and grade ground truth, which weren't provided.
"""

import argparse
import json
from collections import defaultdict


def load_results(path):
    with open(path, "r") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(
            f"{path} is not a list of per-image results. If you ran evaluate.py "
            f"against this file, it overwrote it with a different schema -- "
            f"re-run run_workflow.py to regenerate it."
        )
    return data


def to_corners(box):
    """Convert a center-xywh box dict to (x1, y1, x2, y2) corners."""
    x1 = box["x"] - box["width"] / 2
    y1 = box["y"] - box["height"] / 2
    x2 = box["x"] + box["width"] / 2
    y2 = box["y"] + box["height"] / 2
    return x1, y1, x2, y2


def iou(box_a, box_b):
    """Intersection-over-Union of two center-xywh boxes."""
    ax1, ay1, ax2, ay2 = to_corners(box_a)
    bx1, by1, bx2, by2 = to_corners(box_b)

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area

    if union <= 0:
        return 0.0
    return inter_area / union


def remap_class(cls, group_map):
    return group_map.get(cls, cls) if group_map else cls


def build_group_map(class_names, group_fungus_dark_spot):
    """If enabled, map both 'fungus' and 'dark_spot' to a single label so they
    are treated as interchangeable, matching the report's existing
    methodology note."""
    if not group_fungus_dark_spot:
        return None
    group_map = {}
    if "fungus" in class_names and "dark_spot" in class_names:
        group_map["fungus"] = "fungus_or_dark_spot"
        group_map["dark_spot"] = "fungus_or_dark_spot"
    return group_map


def collect_detections(results, class_names, group_map):
    """Flatten all predictions and ground-truth boxes across images into
    per-class lists, carrying an image index so matching stays within an
    image. Also warns (once) if gt_boxes / image dimensions are missing."""
    preds_by_class = defaultdict(list)   # class -> [(img_idx, confidence, box)]
    gts_by_class = defaultdict(list)     # class -> [(img_idx, box)]
    missing_gt_warned = False

    for img_idx, entry in enumerate(results):
        gt_boxes = entry.get("gt_boxes", [])
        if not gt_boxes and entry.get("expected_classes") and not missing_gt_warned:
            print(
                "  WARNING: entries have expected_classes but no gt_boxes -- "
                "this evaluation_results.json predates the run_workflow.py GT-box "
                "change. Re-run run_workflow.py before trusting these numbers."
            )
            missing_gt_warned = True

        for box in gt_boxes:
            cls = remap_class(box["class"], group_map)
            gts_by_class[cls].append((img_idx, box))

        for pred in entry.get("predictions", []):
            if pred.get("x") is None or pred.get("confidence") is None:
                continue
            cls = remap_class(pred["class"], group_map)
            box = {"x": pred["x"], "y": pred["y"], "width": pred["width"], "height": pred["height"]}
            preds_by_class[cls].append((img_idx, pred["confidence"], box))

    return preds_by_class, gts_by_class


def match_and_score(preds, gts, iou_thresh):
    """Greedy confidence-sorted matching for ONE class.
    preds: [(img_idx, confidence, box)], gts: [(img_idx, box)]
    Returns (tp_flags, confidences) aligned by descending confidence, and n_gt.
    """
    preds_sorted = sorted(preds, key=lambda p: p[1], reverse=True)
    # matched[img_idx] = set of gt indices (within that image's gt list) already used
    gts_by_image = defaultdict(list)
    for gt_idx, (img_idx, box) in enumerate(gts):
        gts_by_image[img_idx].append((gt_idx, box))
    matched_gt = set()

    tp_flags = []
    confidences = []
    for img_idx, conf, pbox in preds_sorted:
        best_iou = 0.0
        best_gt_idx = None
        for gt_idx, gbox in gts_by_image.get(img_idx, []):
            if gt_idx in matched_gt:
                continue
            i = iou(pbox, gbox)
            if i > best_iou:
                best_iou = i
                best_gt_idx = gt_idx
        if best_iou >= iou_thresh and best_gt_idx is not None:
            tp_flags.append(1)
            matched_gt.add(best_gt_idx)
        else:
            tp_flags.append(0)
        confidences.append(conf)

    return tp_flags, confidences, len(gts)


def compute_ap(tp_flags, n_gt):
    """Standard continuous-integration Average Precision from a confidence-sorted
    list of TP(1)/FP(0) flags, matching the convention used by COCO/YOLO mAP."""
    if n_gt == 0:
        return 0.0
    cum_tp = 0
    cum_fp = 0
    precisions = []
    recalls = []
    for flag in tp_flags:
        if flag:
            cum_tp += 1
        else:
            cum_fp += 1
        precisions.append(cum_tp / (cum_tp + cum_fp))
        recalls.append(cum_tp / n_gt)

    if not precisions:
        return 0.0

    # Make precision monotonically non-increasing from the right (standard envelope)
    for i in range(len(precisions) - 2, -1, -1):
        precisions[i] = max(precisions[i], precisions[i + 1])

    # Integrate area under the precision-recall curve
    ap = 0.0
    prev_recall = 0.0
    for p, r in zip(precisions, recalls):
        ap += p * (r - prev_recall)
        prev_recall = r
    return ap


def per_class_metrics(preds_by_class, gts_by_class, class_names, iou_thresh):
    """Returns dict: class -> {precision, recall, f1, ap, tp, fp, fn, n_gt}
    Precision/recall/F1 are at the OPERATING POINT (all predictions as returned).
    AP is threshold-independent (mAP@iou_thresh)."""
    metrics = {}
    for cls in class_names:
        preds = preds_by_class.get(cls, [])
        gts = gts_by_class.get(cls, [])
        tp_flags, confidences, n_gt = match_and_score(preds, gts, iou_thresh)

        tp = sum(tp_flags)
        fp = len(tp_flags) - tp
        fn = n_gt - tp

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / n_gt if n_gt > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        ap = compute_ap(tp_flags, n_gt)

        metrics[cls] = {
            "precision": precision, "recall": recall, "f1": f1, "ap": ap,
            "tp": tp, "fp": fp, "fn": fn, "n_gt": n_gt,
        }
    return metrics


def build_confusion_matrix(results, class_names, iou_thresh, group_map):
    """Cross-class greedy IoU matching per image: for each prediction, find the
    highest-IoU ground-truth box of ANY class (not just the same class) to see
    what the model confused it with. Adds 'background' for FPs (predicted
    something with no matching GT box) and for FNs (GT box with no matching
    prediction).
    Matrix[gt_label][pred_label] = count. gt_label/pred_label include
    'background'.
    """
    labels = [remap_class(c, group_map) for c in class_names]
    labels = list(dict.fromkeys(labels))  # dedupe, preserve order (grouping collapses pairs)
    all_labels = labels + ["background"]
    matrix = {g: {p: 0 for p in all_labels} for g in all_labels}

    for entry in results:
        gt_boxes = [dict(b, _class=remap_class(b["class"], group_map)) for b in entry.get("gt_boxes", [])]
        preds = []
        for pred in entry.get("predictions", []):
            if pred.get("x") is None:
                continue
            preds.append({
                "x": pred["x"], "y": pred["y"], "width": pred["width"], "height": pred["height"],
                "_class": remap_class(pred["class"], group_map),
            })

        matched_gt = set()
        matched_pred = set()

        # Greedy: sort all (pred, gt) pairs by IoU descending, assign matches first
        pairs = []
        for pi, pbox in enumerate(preds):
            for gi, gbox in enumerate(gt_boxes):
                i = iou(pbox, gbox)
                if i >= iou_thresh:
                    pairs.append((i, pi, gi))
        pairs.sort(key=lambda t: t[0], reverse=True)

        for i, pi, gi in pairs:
            if pi in matched_pred or gi in matched_gt:
                continue
            matched_pred.add(pi)
            matched_gt.add(gi)
            gt_label = gt_boxes[gi]["_class"]
            pred_label = preds[pi]["_class"]
            matrix[gt_label][pred_label] += 1

        for pi, pbox in enumerate(preds):
            if pi not in matched_pred:
                matrix["background"][pbox["_class"]] += 1  # false positive
        for gi, gbox in enumerate(gt_boxes):
            if gi not in matched_gt:
                matrix[gbox["_class"]]["background"] += 1  # false negative (missed)

    return matrix, all_labels


def print_table(headers, rows):
    widths = [max(len(str(h)), *(len(str(r[i])) for r in rows)) if rows else len(str(h))
              for i, h in enumerate(headers)]
    def fmt_row(r):
        return "  ".join(str(c).ljust(w) for c, w in zip(r, widths))
    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print(fmt_row(r))


def main():
    parser = argparse.ArgumentParser(description="Compute IoU-based detection benchmarks from evaluation_results.json")
    parser.add_argument("--results", default="evaluation_results.json", help="Path to run_workflow.py's output")
    parser.add_argument("--classes", nargs="+", default=["crack", "dark_spot", "fungus", "thorn_split"])
    parser.add_argument("--iou-thresh", type=float, default=0.5)
    parser.add_argument("--group-fungus-dark-spot", action="store_true",
                         help="Treat fungus and dark_spot predictions as interchangeable (matches report methodology note)")
    parser.add_argument("--out-json", default="benchmark_results.json")
    parser.add_argument("--out-md", default="benchmark_results.md")
    args = parser.parse_args()

    results = load_results(args.results)
    group_map = build_group_map(args.classes, args.group_fungus_dark_spot)
    preds_by_class, gts_by_class = collect_detections(results, args.classes, group_map)

    class_names = list(dict.fromkeys(remap_class(c, group_map) for c in args.classes))
    metrics = per_class_metrics(preds_by_class, gts_by_class, class_names, args.iou_thresh)

    total_tp = sum(m["tp"] for m in metrics.values())
    total_fp = sum(m["fp"] for m in metrics.values())
    total_fn = sum(m["fn"] for m in metrics.values())
    micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)) if (micro_p + micro_r) else 0.0
    macro_p = sum(m["precision"] for m in metrics.values()) / len(metrics) if metrics else 0.0
    macro_r = sum(m["recall"] for m in metrics.values()) / len(metrics) if metrics else 0.0
    macro_f1 = sum(m["f1"] for m in metrics.values()) / len(metrics) if metrics else 0.0
    map_at_iou = sum(m["ap"] for m in metrics.values()) / len(metrics) if metrics else 0.0

    print(f"\n=== Per-class metrics (IoU >= {args.iou_thresh}, at deployed confidence threshold) ===")
    rows = []
    for cls in class_names:
        m = metrics[cls]
        rows.append([cls, m["n_gt"], m["tp"], m["fp"], m["fn"],
                     f"{m['precision']:.3f}", f"{m['recall']:.3f}", f"{m['f1']:.3f}", f"{m['ap']:.3f}"])
    print_table(["class", "n_gt", "TP", "FP", "FN", "precision", "recall", "f1", f"AP@{args.iou_thresh}"], rows)

    print(f"\n=== Overall ===")
    print(f"  Micro precision/recall/F1: {micro_p:.3f} / {micro_r:.3f} / {micro_f1:.3f}")
    print(f"  Macro precision/recall/F1: {macro_p:.3f} / {macro_r:.3f} / {macro_f1:.3f}")
    print(f"  mAP@{args.iou_thresh}: {map_at_iou:.3f}")

    matrix, labels = build_confusion_matrix(results, args.classes, args.iou_thresh, group_map)
    print(f"\n=== Confusion matrix (rows = ground truth, cols = predicted; IoU >= {args.iou_thresh}) ===")
    header = ["GT \\ Pred"] + labels
    rows = []
    for g in labels:
        rows.append([g] + [matrix[g][p] for p in labels])
    print_table(header, rows)

    # ---- Write outputs ----
    output = {
        "iou_threshold": args.iou_thresh,
        "grouped_fungus_dark_spot": bool(args.group_fungus_dark_spot),
        "per_class": {cls: metrics[cls] for cls in class_names},
        "overall": {
            "micro_precision": micro_p, "micro_recall": micro_r, "micro_f1": micro_f1,
            "macro_precision": macro_p, "macro_recall": macro_r, "macro_f1": macro_f1,
            f"mAP@{args.iou_thresh}": map_at_iou,
        },
        "confusion_matrix": {"labels": labels, "matrix": matrix},
    }
    with open(args.out_json, "w") as f:
        json.dump(output, f, indent=2)

    with open(args.out_md, "w") as f:
        f.write(f"### Precision / Recall / F1 / AP (IoU >= {args.iou_thresh})\n\n")
        f.write("| Class | GT | TP | FP | FN | Precision | Recall | F1 | AP@{:.1f} |\n".format(args.iou_thresh))
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for cls in class_names:
            m = metrics[cls]
            f.write(f"| `{cls}` | {m['n_gt']} | {m['tp']} | {m['fp']} | {m['fn']} | "
                    f"{m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['ap']:.3f} |\n")
        f.write(f"\n**Micro P/R/F1:** {micro_p:.3f} / {micro_r:.3f} / {micro_f1:.3f}  \n")
        f.write(f"**Macro P/R/F1:** {macro_p:.3f} / {macro_r:.3f} / {macro_f1:.3f}  \n")
        f.write(f"**mAP@{args.iou_thresh}:** {map_at_iou:.3f}\n\n")
        f.write("### Confusion Matrix (rows = ground truth, cols = predicted)\n\n")
        f.write("| GT \\\\ Pred | " + " | ".join(labels) + " |\n")
        f.write("|---" * (len(labels) + 1) + "|\n")
        for g in labels:
            f.write(f"| `{g}` | " + " | ".join(str(matrix[g][p]) for p in labels) + " |\n")

    print(f"\nWrote {args.out_json} and {args.out_md}")


if __name__ == "__main__":
    main()
