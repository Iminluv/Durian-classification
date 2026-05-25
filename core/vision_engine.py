import os
import sys
import platform
import json
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.logger import logger
from core.backends.onnx_backend import ONNXBackend
from core.backends.openvino_backend import OpenVINOBackend, OPENVINO_AVAILABLE
from core.backends.coreml_backend import CoreMLBackend, COREML_AVAILABLE

class VisionEngine:
    def __init__(self, model_dir: str):
        self.model_dir = Path(model_dir)
        self.conf_thresholds = {
            "crack": 0.60,
            "dark_spot": 0.60,
            "fungus": 0.40,
            "thorn_split": 0.55,
            "reject": 0.35
        }
        self.load_thresholds()
        self.runtime = self._detect_runtime()

    def load_thresholds(self, rules_path="config/rules.json"):
        if os.path.exists(rules_path):
            try:
                with open(rules_path, "r") as f:
                    rules = json.load(f)
                    self.conf_thresholds = rules.get("confidence_thresholds", self.conf_thresholds)
                logger.info(f"Loaded confidence thresholds from {rules_path}: {self.conf_thresholds}")
            except Exception as e:
                logger.error(f"Error loading thresholds: {e}. Using defaults.")

    def _detect_runtime(self):
        sys_platform = platform.system()
        machine = platform.machine().lower()
        
        # 1. macOS ARM64 -> CoreML
        if sys_platform == "Darwin" and ("arm64" in machine or "aarch64" in machine):
            logger.info("Apple Silicon macOS detected. Targeting CoreML backend.")
            coreml_path = self.model_dir / "coreml" / "best.mlpackage"
            if coreml_path.exists() and COREML_AVAILABLE:
                try:
                    return CoreMLBackend(str(coreml_path))
                except Exception as e:
                    logger.error(f"Failed to load CoreML backend: {e}. Falling back to ONNX.")
            else:
                logger.warning("CoreML weights or coremltools not available. Falling back to ONNX.")
                
        # 2. Windows/Intel -> OpenVINO
        elif sys_platform == "Windows" or (sys_platform == "Linux" and ("x86" in machine or "amd64" in machine)):
            logger.info("Intel/AMD architecture detected. Targeting OpenVINO backend.")
            openvino_path = self.model_dir / "openvino" / "best.xml"
            if openvino_path.exists() and OPENVINO_AVAILABLE:
                try:
                    return OpenVINOBackend(str(openvino_path))
                except Exception as e:
                    logger.error(f"Failed to load OpenVINO backend: {e}. Falling back to ONNX.")
            else:
                logger.warning("OpenVINO XML weights or openvino runtime not available. Falling back to ONNX.")

        # 3. Fallback -> ONNX Runtime
        logger.info("Targeting ONNX Runtime backend.")
        onnx_path = self.model_dir / "best.onnx"
        
        if onnx_path.exists():
            return ONNXBackend(str(onnx_path))
        else:
            # Check if there is an onnx file in the model_dir root
            onnx_files = list(self.model_dir.glob("*.onnx"))
            if onnx_files:
                return ONNXBackend(str(onnx_files[0]))
            
            # Universal fallback: try loading from root best.onnx if available
            root_onnx = Path("best.onnx")
            if root_onnx.exists():
                logger.warning("best.onnx found at root directory. Loading as fallback.")
                return ONNXBackend(str(root_onnx))
                
            # If no model files exist yet (e.g. before Phase 2 training output is compiled),
            # return a Mock backend or raise exception depending on usage.
            # In testing, we can raise or return a mock.
            logger.warning(f"No ONNX model found in {self.model_dir}. Returning Mock for initial setup.")
            return MockBackend()

    def infer(self, frame) -> list[dict]:
        if isinstance(self.runtime, MockBackend):
            return self.runtime.infer(frame, self.conf_thresholds)
        return self.runtime.infer(frame, self.conf_thresholds)

class MockBackend:
    def __init__(self):
        logger.info("Mock Vision Backend initialized (no weights found).")
        self.class_names = ['crack', 'dark_spot', 'fungus', 'thorn_split', 'reject']

    def infer(self, frame, conf_thresholds: dict) -> list[dict]:
        # Return empty detections in mock
        return []
