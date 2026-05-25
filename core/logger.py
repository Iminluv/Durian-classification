import os
import json
import logging
import datetime
from pathlib import Path

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "line_no": record.lineno
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

def setup_logger(name="durian_classifier", config_path="config/app.json"):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    # Default settings
    log_level = logging.INFO
    log_format = "json"

    # Attempt to load from config
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                level_str = config.get("log_level", "INFO").upper()
                log_level = getattr(logging, level_str, logging.INFO)
                log_format = config.get("log_format", "json").lower()
        except Exception:
            pass

    logger.setLevel(log_level)
    handler = logging.StreamHandler()
    
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
        )
        
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = setup_logger()
