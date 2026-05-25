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
    from openvino.runtime import Core
    OPENVINO_AVAILABLE = True
except ImportError:
    OPENVINO_AVAILABLE = False

class OpenVINOBackend:
    def __init__(self, model_path: str):
        if not OPENVINO_AVAILABLE:
            raise ImportError("OpenVINO is not available. Please install openvino packages.")
            
        logger.info(f"Loading OpenVINO model from: {model_path}")
        self.core = Core()
        
        # Support both directory containing xml/bin and direct xml file path
        path = Path(model_path)
        if path.is_dir():
            xml_path = path / "best.xml"
        else:
            xml_path = path
            
        if not xml_path.exists():
            raise FileNotFoundError(f"OpenVINO XML file not found at: {xml_path}")
            
        self.model = self.core.read_model(model=str(xml_path))
        self.compiled_model = self.core.compile_model(model=self.model, device_name="CPU")
        self.input_layer = self.compiled_model.input(0)
        self.output_layer = self.compiled_model.output(0)
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
        
        # Run inference
        results_ov = self.compiled_model([img])[self.output_layer]
        
        # OpenVINO output format for YOLOv8 is identical to ONNX: [1, 4 + nc, 8400]
        output = results_ov[0]  # shape: [4 + nc, 8400]
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
