import os
import sys
import json
import shutil
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tasks.celery_config import celery_app
from core.logger import logger

@celery_app.task(bind=True)
def trigger_retrain_pipeline(self, epochs: int = 15, batch_size: int = 16):
    """
    Celery task that runs the dataset augmentation, model training,
    model export, and model evaluation pipeline in the background.
    """
    self.update_state(state='PROGRESS', meta={'message': 'Starting dataset augmentation...'})
    logger.info("Retraining: Running dataset augmentation...")
    
    try:
        # 1. Run Augmentation
        from core.augment import DatasetAugmenter
        augmenter = DatasetAugmenter(input_dir="durian", output_dir="data/augmented", multiplier=10)
        augmenter.run()
        
        # 2. Run Model Training
        self.update_state(state='PROGRESS', meta={'message': 'Augmentation complete. Starting model training...'})
        logger.info("Retraining: Starting YOLO model training...")
        
        from train import train_model
        # Fine-tune using root best.pt if exists, otherwise train from scratch using yolov26n.yaml
        pretrained = "best.pt" if os.path.exists("best.pt") else "yolov26n.pt"
        
        # Run training
        train_model(
            data_cfg="durian.yaml",
            model_type="yolov26n.yaml",
            pretrained_weights=pretrained,
            epochs=epochs,
            imgsz=640,
            batch_size=batch_size,
            device="cpu"  # runs on CPU/MPS automatically in train.py
        )
        
        # 3. Export new model
        self.update_state(state='PROGRESS', meta={'message': 'Model training complete. Exporting formats...'})
        logger.info("Retraining: Exporting model to ONNX, OpenVINO, and CoreML...")
        
        # Check output best.pt from runs/detect/train_durian/weights/best.pt
        best_pt_path = Path("runs/detect/train_durian/weights/best.pt")
        if not best_pt_path.exists() and os.path.exists("best.pt"):
            best_pt_path = Path("best.pt")
            
        if not best_pt_path.exists():
            raise FileNotFoundError("Could not find newly trained model best.pt weight file.")

        from export_model import export_model
        # Export to a temporary directory first for pending review
        temp_export_dir = Path("models/pending_model")
        if temp_export_dir.exists():
            shutil.rmtree(temp_export_dir)
            
        export_model(weights_path=str(best_pt_path), output_dir=str(temp_export_dir))
        
        # 4. Evaluate new model
        self.update_state(state='PROGRESS', meta={'message': 'Export complete. Running validation...'})
        logger.info("Retraining: Running evaluation on the test set...")
        
        from evaluate import evaluate_model
        # Run evaluation on the newly exported ONNX format (universal fallback)
        metrics = evaluate_model(
            model_path=str(temp_export_dir / "best.onnx"),
            data_cfg="durian.yaml",
            benchmark=True,
            runtime="onnx"
        )
        
        # Compare with current model metrics
        current_metrics = {"mAP50": 0.0, "recall_fungus": 0.0, "recall_reject": 0.0, "latency_ms": 0.0}
        if os.path.exists("evaluation_results.json"):
            try:
                with open("evaluation_results.json", "r") as f:
                    current_metrics = json.load(f)
            except Exception:
                pass
                
        # 5. Write pending update for OTA approval prompt in UI
        pending_update_info = {
            "status": "pending_approval",
            "timestamp": time.time(),
            "temp_model_dir": str(temp_export_dir),
            "new_metrics": metrics,
            "current_metrics": current_metrics
        }
        
        pending_config_path = Path("config/pending_model.json")
        pending_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pending_config_path, "w") as f:
            json.dump(pending_update_info, f, indent=4)
            
        logger.info(f"Retraining complete. Saved pending model configuration to {pending_config_path}.")
        return {
            "status": "success",
            "message": "Retraining completed. Pending operator confirmation.",
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Error in retraining task pipeline: {e}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        return {"status": "failed", "error": str(e)}

import time
