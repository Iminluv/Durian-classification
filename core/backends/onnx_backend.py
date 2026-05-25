import os
import sys
import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.logger import logger

class ONNXBackend:
    def __init__(self, model_path: str):
        logger.info(f"Loading ONNX model from: {model_path}")
        self.session = ort.InferenceSession(model_path)
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape  # [1, 3, 640, 640]
        self.output_names = [o.name for o in self.session.get_outputs()]
        self.class_names = ['crack', 'dark_spot', 'fungus', 'thorn_split', 'reject']

    def preprocess(self, frame):
        h, w = frame.shape[:2]
        img = cv2.resize(frame, (640, 640))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = img.transpose(2, 0, 1)  # HWC to CHW
        img = np.expand_dims(img, axis=0)  # Add batch dim
        return img, h, w

    def infer(self, frame, conf_thresholds: dict) -> list[dict]:
        img, orig_h, orig_w = self.preprocess(frame)
        
        # Run model
        outputs = self.session.run(self.output_names, {self.input_name: img})
        
        # YOLO output is typically of shape [1, 4 + nc, 8400]
        # output shape -> [4 + nc, 8400]
        output = outputs[0][0]
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
            # OpenCV NMSBoxes returns 1D array or 2D array depending on OpenCV version
            indices_flat = np.array(indices).flatten()
            for idx in indices_flat:
                box = selected_boxes[idx]
                results.append({
                    "class": self.class_names[selected_class_ids[idx]],
                    "bbox": [max(0, box[0]), max(0, box[1]), box[2], box[3]],  # [x, y, w, h]
                    "confidence": selected_scores[idx]
                })
                
        return results
