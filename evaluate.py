import os
import sys
import time
import json
import numpy as np
from pathlib import Path
import torch

# Patch torch.load to default to weights_only=False to support loading YOLO checkpoints in PyTorch 2.6+
orig_load = torch.load
def patched_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return orig_load(*args, **kwargs)
torch.load = patched_load

# Add project root to sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ultralytics import YOLO
from core.logger import logger

def benchmark_latency(model, sample_img_path, num_runs=50):
    if not os.path.exists(sample_img_path):
        logger.warning(f"Benchmark image {sample_img_path} not found. Cannot benchmark latency.")
        return 0.0

    # Warmup
    for _ in range(5):
        _ = model(str(sample_img_path), verbose=False)

    times = []
    for _ in range(num_runs):
        start = time.perf_counter()
        _ = model(str(sample_img_path), verbose=False)
        end = time.perf_counter()
        times.append((end - start) * 1000.0) # in ms

    avg_latency = np.mean(times)
    logger.info(f"Benchmark latency: {avg_latency:.2f} ms per frame (over {num_runs} runs)")
    return avg_latency

def evaluate_model(
    model_path="best.pt", 
    data_cfg="durian.yaml", 
    benchmark=False, 
    runtime="pytorch"
):
    logger.info(f"Evaluating model '{model_path}' using runtime '{runtime}'...")
    
    # Check model path
    if not os.path.exists(model_path):
        logger.error(f"Model path '{model_path}' not found.")
        sys.exit(1)

    # 1. Load model based on runtime
    # If the user specifies openvino/coreml, we load the folder/exported file
    model = YOLO(model_path)
    
    # 2. Standard validation on test split
    # Ultralytics val function has argument 'split' which defaults to 'val', can be set to 'test'
    logger.info("Running validation on the test split...")
    val_results = model.val(data=data_cfg, split="test", verbose=False)
    
    # Extract KPIs
    # classes mapping: ['crack', 'dark_spot', 'fungus', 'thorn_split', 'reject']
    # class indexes:    0        1            2         3              4
    
    # Extract overall metrics
    map50 = val_results.box.map50
    mean_recall = val_results.box.mr
    
    # Extract per-class recall
    # val_results.box.r contains per-class recalls
    per_class_recall = val_results.box.r
    
    recall_fungus = 0.0
    recall_reject = 0.0
    
    if len(per_class_recall) > 2:
        recall_fungus = per_class_recall[2]
    if len(per_class_recall) > 4:
        recall_reject = per_class_recall[4]
        
    logger.info(f"Evaluation Results:")
    logger.info(f"  mAP@50: {map50 * 100:.2f}% (Target: >= 70%)")
    logger.info(f"  Recall (fungus): {recall_fungus * 100:.2f}% (Target: >= 85%)")
    logger.info(f"  Recall (reject): {recall_reject * 100:.2f}% (Target: >= 85%)")
    logger.info(f"  Mean Recall: {mean_recall * 100:.2f}%")
    
    # Check KPI gates
    kpi_passed = True
    if map50 < 0.70:
        logger.warning("KPI GATE FAILED: mAP@50 overall < 70%")
        kpi_passed = False
    if recall_fungus < 0.85:
        logger.warning("KPI GATE FAILED: Recall (fungus) < 85%")
        kpi_passed = False
    if recall_reject < 0.85:
        logger.warning("KPI GATE FAILED: Recall (reject) < 85%")
        kpi_passed = False
        
    if kpi_passed:
        logger.info("ALL ACCURACY/RECALL KPI GATES PASSED!")
    else:
        logger.warning("SOME ACCURACY/RECALL KPI GATES FAILED.")

    # 3. Latency benchmark
    latency_ms = 0.0
    if benchmark:
        # Find a sample image in the test dataset
        # data_cfg config has path. We can search in data/augmented/test/images
        # Let's read path from durian.yaml or fallback to hardcoded
        test_images_dir = Path("data/augmented/test/images")
        sample_img = None
        if test_images_dir.exists():
            sample_imgs = list(test_images_dir.glob("*.jpg")) + list(test_images_dir.glob("*.png"))
            if sample_imgs:
                sample_img = sample_imgs[0]
                
        if not sample_img and os.path.exists("durian/test/images"):
            sample_imgs = list(Path("durian/test/images").glob("*.jpg"))
            if sample_imgs:
                sample_img = sample_imgs[0]

        if sample_img:
            logger.info(f"Using benchmark image: {sample_img}")
            latency_ms = benchmark_latency(model, sample_img)
            
            # Latency gates
            import platform
            system = platform.system()
            if runtime == "openvino":
                if latency_ms < 200.0:
                    logger.info("LATENCY KPI PASSED: OpenVINO < 200ms")
                else:
                    logger.warning("LATENCY KPI FAILED: OpenVINO >= 200ms")
            elif runtime == "coreml":
                if latency_ms < 100.0:
                    logger.info("LATENCY KPI PASSED: CoreML < 100ms")
                else:
                    logger.warning("LATENCY KPI FAILED: CoreML >= 100ms")
        else:
            logger.warning("No sample test images found to run latency benchmark.")

    # Write evaluation metrics JSON for reporting
    results_dict = {
        "mAP50": float(map50),
        "recall_fungus": float(recall_fungus),
        "recall_reject": float(recall_reject),
        "kpi_passed": bool(kpi_passed),
        "latency_ms": float(latency_ms),
        "runtime": runtime
    }
    
    with open("evaluation_results.json", "w") as f:
        json.dump(results_dict, f, indent=4)
        logger.info("Saved metrics to evaluation_results.json")

    return results_dict

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate YOLOv8 model and verify KPI gates")
    parser.add_argument("--weights", default="best.pt", help="Path to model weights or exported model folder")
    parser.add_argument("--data", default="durian.yaml", help="Path to YOLO dataset config")
    parser.add_argument("--benchmark", action="store_true", help="Perform inference latency benchmark")
    parser.add_argument("--runtime", default="pytorch", choices=["pytorch", "openvino", "coreml", "onnx"], help="Inference runtime to use")
    args = parser.parse_args()

    evaluate_model(
        model_path=args.weights,
        data_cfg=args.data,
        benchmark=args.benchmark,
        runtime=args.runtime
    )
