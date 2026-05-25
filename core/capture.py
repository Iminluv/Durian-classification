import os
import sys
import cv2
import time
import datetime
import json
import numpy as np
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.logger import logger

class CameraCapture:
    def __init__(self, config_path="config/camera.json", batch_id=None):
        self.config_path = config_path
        self.batch_id = batch_id or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.load_config()
        self.cap = None
        self.running = False
        self.prev_frame = None

    def load_config(self):
        default_config = {
            "source_type": "usb",
            "usb_device_id": 0,
            "rtsp_url": "rtsp://192.168.1.100:554/stream",
            "capture_fps": 5,
            "motion_threshold": 25,
            "jpeg_quality": 80,
            "output_dir": "data/raw"
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    self.config = json.load(f)
                logger.info(f"Loaded camera config from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading camera config: {e}. Using defaults.")
                self.config = default_config
        else:
            logger.warning(f"Config file {self.config_path} not found. Using defaults.")
            self.config = default_config

        self.source_type = self.config.get("source_type", "usb")
        self.usb_device_id = self.config.get("usb_device_id", 0)
        self.rtsp_url = self.config.get("rtsp_url", "")
        self.capture_fps = self.config.get("capture_fps", 5)
        self.motion_threshold = self.config.get("motion_threshold", 25)
        self.jpeg_quality = self.config.get("jpeg_quality", 80)
        self.output_dir = self.config.get("output_dir", "data/raw")

    def initialize_camera(self):
        if self.source_type == "usb":
            logger.info(f"Initializing USB camera (ID: {self.usb_device_id})")
            self.cap = cv2.VideoCapture(self.usb_device_id)
        elif self.source_type == "rtsp":
            logger.info(f"Initializing RTSP camera (URL: {self.rtsp_url})")
            self.cap = cv2.VideoCapture(self.rtsp_url)
        else:
            logger.error(f"Unknown camera source type: {self.source_type}")
            return False

        if not self.cap.isOpened():
            logger.error("Failed to open camera capture source.")
            return False
        
        # Set buffer size if possible to prevent delay
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return True

    def detect_motion(self, frame):
        """Calculate percentage of frame change between current and previous frame."""
        if self.prev_frame is None:
            # First frame, convert and store
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self.prev_frame = cv2.GaussianBlur(gray, (21, 21), 0)
            return 0.0

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_blur = cv2.GaussianBlur(gray, (21, 21), 0)

        # Compute difference
        frame_delta = cv2.absdiff(self.prev_frame, gray_blur)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        
        # Dilate to fill holes
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Calculate percentage of motion pixels
        motion_pixel_ratio = (np.sum(thresh == 255) / thresh.size) * 100
        
        # Update prev frame
        self.prev_frame = gray_blur
        
        return motion_pixel_ratio

    def get_output_path(self):
        date_str = datetime.date.today().strftime("%Y-%m-%d")
        path = Path(self.output_dir) / date_str / self.batch_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run(self):
        if not self.initialize_camera():
            return

        self.running = True
        logger.info("Camera capture loop started.")
        
        # Calculate frame sleep time
        sleep_time = 1.0 / self.capture_fps if self.capture_fps > 0 else 0.1
        last_capture_time = 0
        cooldown_time = 1.0  # limit capture to max 1 frame per second to avoid flooding

        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("Failed to grab frame from camera.")
                    time.sleep(0.5)
                    continue

                motion_score = self.detect_motion(frame)
                
                # Check motion trigger
                now = time.time()
                if motion_score >= self.motion_threshold and (now - last_capture_time) >= cooldown_time:
                    output_dir = self.get_output_path()
                    timestamp = datetime.datetime.now().strftime("%H%M%S_%f")
                    filename = f"frame_{timestamp}.jpg"
                    filepath = output_dir / filename
                    
                    # Save frame
                    cv2.imwrite(
                        str(filepath), 
                        frame, 
                        [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
                    )
                    logger.info(f"Motion detected (score: {motion_score:.1f}%). Saved frame: {filepath}")
                    last_capture_time = now

                time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Capture loop interrupted by user.")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
            logger.info("Camera capture released.")
        logger.info("Camera capture service stopped.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Standalone Durian Camera Capture service")
    parser.add_argument("--config", default="config/camera.json", help="Path to camera config file")
    parser.add_argument("--batch", default=None, help="Batch ID for session")
    args = parser.parse_args()

    capture = CameraCapture(config_path=args.config, batch_id=args.batch)
    capture.run()
