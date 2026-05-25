import os
import sys
import shutil
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

def export_model(weights_path="best.pt", output_dir="models/yolov26n_v1"):
    weights = Path(weights_path)
    if not weights.exists():
        logger.error(f"Weights file '{weights_path}' not found. Cannot export.")
        sys.exit(1)

    dest_dir = Path(output_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading YOLO model from {weights_path}...")
    model = YOLO(weights_path)

    # 1. Export to ONNX (universal fallback)
    logger.info("Exporting model to ONNX format...")
    try:
        # opset=17 is specified in the implementation plan
        onnx_path = model.export(format="onnx", imgsz=640, opset=17, simplify=True)
        # Move onnx output to the destination directory
        shutil.move(onnx_path, dest_dir / "best.onnx")
        logger.info(f"ONNX export succeeded: {dest_dir / 'best.onnx'}")
    except Exception as e:
        logger.error(f"ONNX export failed: {e}")

    # 2. Export to OpenVINO IR (Windows production)
    logger.info("Exporting model to OpenVINO IR format...")
    try:
        # half=False (FP32) is specified in the implementation plan
        openvino_dir = model.export(format="openvino", imgsz=640, half=False)
        openvino_dest = dest_dir / "openvino"
        if openvino_dest.exists():
            shutil.rmtree(openvino_dest)
        shutil.move(openvino_dir, openvino_dest)
        logger.info(f"OpenVINO export succeeded: {openvino_dest}")
    except Exception as e:
        logger.error(f"OpenVINO export failed: {e}")

    # 3. Export to CoreML (Mac dev/testing)
    logger.info("Exporting model to CoreML format...")
    try:
        # half=True (FP16) is specified in the implementation plan
        coreml_dir = model.export(format="coreml", imgsz=640, half=True)
        coreml_dest = dest_dir / "coreml"
        if coreml_dest.exists():
            shutil.rmtree(coreml_dest)
        shutil.move(coreml_dir, coreml_dest)
        logger.info(f"CoreML export succeeded: {coreml_dest}")
    except Exception as e:
        logger.error(f"CoreML export failed: {e}")

    # Copy the original pytorch file too
    shutil.copy(weights, dest_dir / "best.pt")
    logger.info(f"Model export process completed. Models saved in {dest_dir}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Export YOLO PyTorch weights to OpenVINO, CoreML, and ONNX formats")
    parser.add_argument("--weights", default="best.pt", help="Path to best.pt weights file")
    parser.add_argument("--output", default="models/yolov26n_v1", help="Output directory for exported models")
    args = parser.parse_args()

    export_model(weights_path=args.weights, output_dir=args.output)
