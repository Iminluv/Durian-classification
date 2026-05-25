import os
import sys
import time
import shutil
import json
import threading
import datetime
from pathlib import Path
from core.logger import logger

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class DBBackupService:
    def __init__(self, config_path="config/app.json"):
        self.config_path = Path(config_path)
        self.running = False
        self.thread = None
        self.load_config()

    def load_config(self):
        default_config = {
            "db_path": "data/durian.db",
            "db_backup_interval_minutes": 15,
            "db_backup_max_count": 10
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                logger.info(f"Backup service loaded config from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading app config for backup service: {e}. Using defaults.")
                config = default_config
        else:
            config = default_config

        self.db_path = Path(config.get("db_path", "data/durian.db"))
        self.backup_interval_seconds = config.get("db_backup_interval_minutes", 15) * 60
        self.max_backups = config.get("db_backup_max_count", 10)
        self.backup_dir = self.db_path.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def start(self):
        if self.running:
            logger.warning("Backup service is already running.")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info(f"Database backup service started. Interval: {self.backup_interval_seconds / 60:.1f} minutes.")

    def stop(self):
        self.running = False
        logger.info("Database backup service stopped.")

    def perform_backup(self):
        if not self.db_path.exists():
            logger.warning(f"Database file {self.db_path} does not exist. Cannot backup.")
            return

        # Reload config in case it changed
        self.load_config()

        # Run checkpoint first to flush changes to main DB
        try:
            from core.database import db_manager
            db_manager.checkpoint_db()
        except Exception as e:
            logger.error(f"Failed checkpoint before backup: {e}")

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"durian_{timestamp}.db"
        dest_path = self.backup_dir / backup_name

        try:
            shutil.copy2(self.db_path, dest_path)
            logger.info(f"Successfully backed up database to: {dest_path}")
            self._cleanup_old_backups()
        except Exception as e:
            logger.error(f"Failed to copy database during backup: {e}")

    def _cleanup_old_backups(self):
        try:
            # List backups sorted by creation time
            backups = sorted(
                list(self.backup_dir.glob("durian_*.db")),
                key=lambda p: p.stat().st_mtime
            )
            
            # Delete oldest if count exceeds max_backups
            if len(backups) > self.max_backups:
                to_delete = backups[:-self.max_backups]
                for p in to_delete:
                    p.unlink()
                    logger.info(f"Deleted old database backup file: {p.name}")
        except Exception as e:
            logger.error(f"Error cleaning up old database backups: {e}")

    def _run_loop(self):
        while self.running:
            # Wait for interval, check running status periodically to allow fast shutdown
            start_wait = time.time()
            while self.running and (time.time() - start_wait) < self.backup_interval_seconds:
                time.sleep(1.0)
            
            if self.running:
                self.perform_backup()

if __name__ == "__main__":
    service = DBBackupService()
    service.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop()
