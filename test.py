from ultralytics import YOLO
import os, json
from pathlib import Path

# Paths to test images and labels
TEST_IMAGES = "durian/test/images"
TEST_LABELS = "durian/test/labels"  # YOLO txt ground truth files

# Model loading logic: try local best.pt first, fallback to Roboflow API
weights_path = "best.pt"
if os.path.exists(weights_path):
    print("Loading model from local weights (best.pt)...")
    model = YOLO(weights_path)
else:
    print("Local weights 'best.pt' not found. Attempting to use Roboflow API...")
    api_key = os.getenv("ROBOFLOW_API_KEY")
    if not api_key:
        print("\nERROR: Local weights file 'best.pt' not found, and ROBOFLOW_API_KEY environment variable is not set.")
        print("Please set your Roboflow API key by running the script like this:")
        print("  ROBOFLOW_API_KEY=\"your_api_key\" python test.py\n")
        exit(1)
        
    from roboflow import Roboflow
    rf = Roboflow(api_key=api_key)
    project = rf.workspace("phongs-workspace-kigpq").project("durian-tcen8-nf4tn")
    model = project.version(1).model

def get_gt_classes(label_path):
    """Read ground truth class IDs from YOLO txt file."""
    if not os.path.exists(label_path):
        return set()
    with open(label_path) as f:
        return set(int(line.split()[0]) for line in f.readlines())

def image_level_hit_rate(model, images_dir, labels_dir, conf=0.35):
    total, hits = 0, 0
    misses = []

    for img_path in Path(images_dir).glob("*.jpg"):
        label_path = Path(labels_dir) / (img_path.stem + ".txt")
        gt_classes   = get_gt_classes(label_path)

        if not gt_classes:
            continue  # skip unannotated images

        # Predict using either Roboflow API or local YOLO model
        if hasattr(model, "predict"):
            res = model.predict(str(img_path), confidence=int(conf * 100)).json()
            pred_classes = set(int(pred["class_id"]) for pred in res.get("predictions", []))
        else:
            results      = model(str(img_path), conf=conf, verbose=False)
            pred_classes = set(int(c) for c in results[0].boxes.cls.tolist())

        # Treat 'dark_spot' (1) and 'fungus' (2) as interchangeable (mismatches count as hits)
        effective_pred = pred_classes.copy()
        if 1 in pred_classes or 2 in pred_classes:
            effective_pred.add(1)
            effective_pred.add(2)

        total += 1
        if gt_classes.issubset(effective_pred):
            hits += 1
        else:
            missed = gt_classes - effective_pred
            misses.append({"image": img_path.name, "missed_classes": list(missed)})

    hit_rate = hits / total * 100
    print(f"Image-level hit rate: {hit_rate:.1f}%  ({hits}/{total})")
    print(f"Missed class breakdown:")
    for m in misses:
        print(f"  {m['image']} → missed {m['missed_classes']}")

    return hit_rate, misses

# Run it
hit_rate, misses = image_level_hit_rate(model, TEST_IMAGES, TEST_LABELS, conf=0.6)