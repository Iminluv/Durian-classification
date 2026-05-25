import os
import sys
import cv2
import numpy as np
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.logger import logger

try:
    import coremltools as ct
    COREML_AVAILABLE = True
except ImportError:
    COREML_AVAILABLE = False

class CoreMLBackend:
    def __init__(self, model_path: str):
        if not COREML_AVAILABLE:
            raise ImportError("CoreML is not available. Please install coremltools packages on macOS.")
            
        logger.info(f"Loading CoreML model from: {model_path}")
        
        path = Path(model_path)
        if path.is_dir() and not str(path).endswith(".mlpackage"):
            coreml_path = path / "best.mlpackage"
        else:
            coreml_path = path
            
        if not coreml_path.exists():
            # Try to search for .mlpackage folder inside directory
            packages = list(path.glob("**/*.mlpackage"))
            if packages:
                coreml_path = packages[0]
            else:
                raise FileNotFoundError(f"CoreML package not found at: {coreml_path}")
            
        self.model = ct.models.MLModel(str(coreml_path))
        self.class_names = ['crack', 'dark_spot', 'fungus', 'thorn_split', 'reject']
        
        # Identify input and output names
        spec = self.model.get_spec()
        self.input_name = spec.description.input[0].name
        self.output_name = spec.description.output[0].name
        logger.info(f"CoreML input layer: {self.input_name}, output layer: {self.output_name}")

    def preprocess(self, frame):
        h, w = frame.shape[:2]
        # CoreML model expects PIL image or BGR/RGB array of shape 640x640 depending on conversion
        img = cv2.resize(frame, (640, 640))
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Some CoreML YOLO models expect a PIL Image as input
        from PIL import Image
        pil_img = Image.fromarray(img_rgb)
        return pil_img, h, w

    def infer(self, frame, conf_thresholds: dict) -> list[dict]:
        img, orig_h, orig_w = self.preprocess(frame)
        
        # Run prediction
        # model.predict takes a dict mapping input name to input data
        preds = self.model.predict({self.input_name: img})
        output = preds[self.output_name]
        
        # CoreML outputs can be of shape [1, 4 + nc, 8400] or [4 + nc, 8400]
        if len(output.shape) == 3:
            output = output[0]  # shape: [4 + nc, 8400]
            
        output = output.T  # Transpose to [8400, 4 + nc]
        
        boxes = output[:, :4]
        scores = output[:, 4:]
        
        class_ids = np.argmax(scores, axis=1)
        max_scores = np.max(scores, axis=1)
        
        selected_boxes = []
        selected_scores = []
        selected_class_ids = []
        
        for i in range(len(max_scores)):
            class_id = class_ids[i]
            if class_id >= len(self.class_names):
                continue
            c_name = self.class_names[class_id]
            thresh = conf_thresholds.get(c_name, 0.5)
            
            if max_scores[i] >= thresh:
                cx, cy, bw, bh = boxes[i]
                
                # Convert center coordinates to top-left corner
                x = (cx - bw/2) * (orig_w / 640.0)
                y = (cy - bh/2) * (orig_h / 640.0)
                bw_orig = bw * (orig_w / 640.0)
                bh_orig = bh * (orig_h / 640.0)
                
                selected_boxes.append([int(x), int(y), int(bw_orig), int(bh_orig)])
                selected_scores.append(float(max_scores[i]))
                selected_class_ids.append(int(class_id))
                
        if not selected_boxes:
            return []
            
        # Apply Non-Maximum Suppression (NMS)
        indices = cv2.dnn.NMSBoxes(selected_boxes, selected_scores, 0.1, 0.45)
        
        results = []
        if len(indices) > 0:
            indices_flat = np.array(indices).flatten()
            for idx in indices_flat:
                box = selected_boxes[idx]
                results.append({
                    "class": self.class_names[selected_class_ids[idx]],
                    "bbox": [max(0, box[0]), max(0, box[1]), box[2], box[3]],  # [x, y, w, h]
                    "confidence": selected_scores[idx]
                })
                
        return results
