import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.capture import CameraCapture

class TestCameraCapture(unittest.TestCase):
    def setUp(self):
        self.config_path = "config/camera.json"

    def test_config_loading(self):
        capture = CameraCapture(config_path=self.config_path)
        self.assertEqual(capture.source_type, "usb")
        self.assertEqual(capture.usb_device_id, 0)
        self.assertEqual(capture.motion_threshold, 25)
        self.assertEqual(capture.jpeg_quality, 80)

    def test_motion_detection_no_motion(self):
        capture = CameraCapture(config_path=self.config_path)
        
        # Create two identical frames (grayscale/color doesn't matter, we pass color BGR)
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2 = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # First frame initializes the previous frame reference
        score1 = capture.detect_motion(frame1)
        self.assertEqual(score1, 0.0)
        
        # Second frame is identical, score should be 0.0
        score2 = capture.detect_motion(frame2)
        self.assertEqual(score2, 0.0)

    def test_motion_detection_with_motion(self):
        capture = CameraCapture(config_path=self.config_path)
        
        # Create first frame (all black)
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        # Create second frame (with a big white rectangle in the middle)
        frame2 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2[30:70, 30:70, :] = 255
        
        # First frame initializes
        capture.detect_motion(frame1)
        
        # Second frame has motion, score should be > 0.0
        score = capture.detect_motion(frame2)
        self.assertGreater(score, 0.0)

if __name__ == "__main__":
    unittest.main()
