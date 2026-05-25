import os
import sys
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

import mlflow
from ultralytics import YOLO
from core.logger import logger

def train_model(
    data_cfg="durian.yaml",
    model_type="yolov26n.yaml",  # Train from scratch using YOLOv26n architecture
    pretrained_weights="yolov26n.pt",  # Use pretrained weights if available
    epochs=50,
    imgsz=640,
    batch_size=16,
    device="cpu"  # default to cpu, can be 'mps' on Mac or '0' on GPU
):
    logger.info("Initializing MLflow experiment...")
    mlflow.set_experiment("durian-defect-detection")
    
    # Auto-detect device
    import torch
    if device == "cpu":
        if torch.backends.mps.is_available():
            device = "mps"
            logger.info("Apple Silicon MPS acceleration detected and enabled.")
        elif torch.cuda.is_available():
            device = "0"
            logger.info("CUDA GPU acceleration detected and enabled.")
    
    logger.info(f"Loading model: {model_type} (pretrained: {pretrained_weights})")
    
    # Check if we should use pretrained weights or train from scratch
    if os.path.exists(pretrained_weights):
        logger.info(f"Using local pretrained weights: {pretrained_weights}")
        model = YOLO(pretrained_weights)
    else:
        logger.info(f"Pretrained weights '{pretrained_weights}' not found. Downloading/loading default yolov26n.pt")
        try:
            model = YOLO("yolov26n.pt")
        except Exception as e:
            logger.warning(f"Could not load yolov26n.pt: {e}. Training from scratch using configuration: {model_type}")
            model = YOLO(model_type)

    logger.info(f"Starting training on device: {device} for {epochs} epochs...")
    
    # Start MLflow run
    with mlflow.start_run(run_name="yolov26n_durian_run") as run:
        # Log basic training parameters to MLflow
        mlflow.log_params({
            "epochs": epochs,
            "imgsz": imgsz,
            "batch_size": batch_size,
            "device": device,
            "model_type": model_type
        })
        
        # Train model
        results = model.train(
            data=data_cfg,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch_size,
            device=device,
            project="runs/detect",
            name="train_durian",
            save=True,
            val=True,
            plots=True
        )
        
        logger.info("Training complete.")
        
        # Get path to the best weights
        best_weights_path = Path("runs/detect/train_durian/weights/best.pt")
        if best_weights_path.exists():
            logger.info(f"Found best model weights at: {best_weights_path}")
            # Save a copy to root for quick access
            import shutil
            shutil.copy(best_weights_path, "best.pt")
            
            # Log weights artifact in MLflow
            mlflow.log_artifact("best.pt", artifact_path="model_weights")
        else:
            logger.warning("Could not find training output best.pt weights.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train YOLOv26 model on durian defect dataset")
    parser.add_argument("--data", default="durian.yaml", help="Path to YOLO dataset config yaml")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs") # Small default for testing
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--device", default="cpu", help="Device (cpu, mps, or cuda GPU id)")
    args = parser.parse_args()

    train_model(
        data_cfg=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch_size=args.batch,
        device=args.device
    )
