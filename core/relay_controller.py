import sys
import time
import platform
from core.logger import logger

try:
    import hid
    HID_AVAILABLE = True
except ImportError:
    HID_AVAILABLE = False

class MockRelay:
    def write(self, data):
        logger.info(f"[Mock Relay] Command executed: {data}")
        return len(data)
    
    def close(self):
        logger.info("[Mock Relay] Connection closed.")

class RelayController:
    GRADE_CHANNEL = {"A": 1, "B": 2, "C": 3, "reject": 4}

    def __init__(self, vendor_id=0x16c0, product_id=0x05df, mock=False):
        self.mock_mode = mock or (platform.system() == "Darwin")
        self.device = None

        if not self.mock_mode and HID_AVAILABLE:
            try:
                logger.info(f"Connecting to USB HID relay (VID: 0x{vendor_id:04x}, PID: 0x{product_id:04x})")
                self.device = hid.device()
                self.device.open(vendor_id, product_id)
                logger.info("USB HID relay connected.")
            except Exception as e:
                logger.warning(f"Could not open USB HID relay: {e}. Falling back to mock relay.")
                self.mock_mode = True
        else:
            self.mock_mode = True

        if self.mock_mode:
            logger.info("Operating in Mock Relay mode.")
            self.device = MockRelay()

    def trigger(self, grade: str, pulse_ms: int = 200) -> bool:
        if grade not in self.GRADE_CHANNEL:
            logger.error(f"Failed to trigger relay: Invalid grade '{grade}'")
            return False

        ch = self.GRADE_CHANNEL[grade]
        logger.info(f"Triggering relay channel {ch} for grade '{grade}' ({pulse_ms}ms pulse)")
        try:
            # standard USB HID relay write protocol
            self.device.write([0x00, ch, 0xFF])
            time.sleep(pulse_ms / 1000.0)
            self.device.write([0x00, ch, 0x00])
            return True
        except Exception as e:
            logger.error(f"Failed to write to relay device: {e}")
            return False

    def close(self):
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
