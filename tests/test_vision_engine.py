import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import shutil

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.vision_engine import VisionEngine, MockBackend

class TestVisionEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('core.vision_engine.ONNXBackend')
    @patch('core.vision_engine.platform.system')
    def test_vision_engine_fallback_onnx(self, mock_system, mock_onnx):
        # Force platform to Linux
        mock_system.return_value = "Linux"
        
        # Create a mock ONNX weights file so it is found
        onnx_file = Path(self.test_dir) / "best.onnx"
        onnx_file.touch()

        # Initialize
        engine = VisionEngine(model_dir=self.test_dir)
        
        # Verify ONNXBackend initialized
        mock_onnx.assert_called_once_with(str(onnx_file))
        self.assertNotIsInstance(engine.runtime, MockBackend)

    @patch('core.vision_engine.platform.system')
    def test_vision_engine_fallback_mock(self, mock_system):
        # Force platform to Linux, but no weights files exist in directory
        mock_system.return_value = "Linux"
        
        engine = VisionEngine(model_dir=self.test_dir)
        
        # Should fallback to MockBackend
        self.assertIsInstance(engine.runtime, MockBackend)
        
        # Mock inference returns empty list
        res = engine.infer(None)
        self.assertEqual(res, [])

if __name__ == "__main__":
    unittest.main()
