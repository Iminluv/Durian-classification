import sqlite3
import os
import sys
import json
import datetime
from pathlib import Path
from core.logger import logger

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class DatabaseManager:
    def __init__(self, db_path="data/durian.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.initialize()

    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON;")
        # Enable WAL mode
        conn.execute("PRAGMA journal_mode=WAL;")
        # Enable synchronous normal for WAL safety/speed
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def initialize(self):
        logger.info(f"Initializing SQLite database at: {self.db_path}")
        conn = self.get_connection()
        try:
            with conn:
                # Create batches table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS batches (
                        batch_id      TEXT PRIMARY KEY,
                        start_time    DATETIME,
                        end_time      DATETIME,
                        total_count   INTEGER DEFAULT 0,
                        grade_a       INTEGER DEFAULT 0,
                        grade_b       INTEGER DEFAULT 0,
                        grade_c       INTEGER DEFAULT 0,
                        reject        INTEGER DEFAULT 0
                    );
                """)
                # Create detections table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS detections (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
                        batch_id      TEXT NOT NULL,
                        final_grade   TEXT NOT NULL,
                        defect_types  TEXT,               -- JSON array of detected defect labels
                        defect_count  INTEGER DEFAULT 0,
                        confidence    REAL,
                        image_path    TEXT,
                        overridden    BOOLEAN DEFAULT 0,
                        operator_id   TEXT,
                        FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
                    );
                """)
            logger.info("Database schemas verified successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")
            raise e
        finally:
            conn.close()

    def start_batch(self, batch_id: str, operator_id: str = None) -> bool:
        conn = self.get_connection()
        try:
            with conn:
                now = datetime.datetime.utcnow().isoformat() + "Z"
                conn.execute("""
                    INSERT OR IGNORE INTO batches (batch_id, start_time)
                    VALUES (?, ?);
                """, (batch_id, now))
            logger.info(f"Started batch: {batch_id}")
            return True
        except Exception as e:
            logger.error(f"Error starting batch {batch_id}: {e}")
            return False
        finally:
            conn.close()

    def stop_batch(self, batch_id: str) -> bool:
        conn = self.get_connection()
        try:
            with conn:
                now = datetime.datetime.utcnow().isoformat() + "Z"
                conn.execute("""
                    UPDATE batches 
                    SET end_time = ? 
                    WHERE batch_id = ?;
                """, (now, batch_id))
            logger.info(f"Stopped batch: {batch_id}")
            return True
        except Exception as e:
            logger.error(f"Error stopping batch {batch_id}: {e}")
            return False
        finally:
            conn.close()

    def add_detection(
        self,
        batch_id: str,
        final_grade: str,
        defect_types: list[str],
        defect_count: int,
        confidence: float,
        image_path: str = None,
        operator_id: str = None
    ) -> int:
        conn = self.get_connection()
        try:
            with conn:
                now = datetime.datetime.utcnow().isoformat() + "Z"
                defect_types_str = json.dumps(defect_types)
                
                # Insert detection record
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO detections (timestamp, batch_id, final_grade, defect_types, defect_count, confidence, image_path, operator_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (now, batch_id, final_grade, defect_types_str, defect_count, confidence, image_path, operator_id))
                detection_id = cursor.lastrowid
                
                # Update batch aggregates
                grade_col = f"grade_{final_grade.lower()}" if final_grade.lower() in ["a", "b", "c"] else "reject"
                conn.execute(f"""
                    UPDATE batches 
                    SET total_count = total_count + 1,
                        {grade_col} = {grade_col} + 1
                    WHERE batch_id = ?;
                """, (batch_id,))
                
            return detection_id
        except Exception as e:
            logger.error(f"Error saving detection to database: {e}")
            return -1
        finally:
            conn.close()

    def get_batch_summary(self, batch_id: str) -> dict:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM batches WHERE batch_id = ?;", (batch_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}
        except Exception as e:
            logger.error(f"Error fetching batch summary: {e}")
            return {}
        finally:
            conn.close()

    def get_detections_history(self, limit: int = 100, offset: int = 0, batch_id: str = None) -> list[dict]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if batch_id:
                cursor.execute("""
                    SELECT * FROM detections 
                    WHERE batch_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT ? OFFSET ?;
                """, (batch_id, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM detections 
                    ORDER BY timestamp DESC 
                    LIMIT ? OFFSET ?;
                """, (limit, offset))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error fetching detections: {e}")
            return []
        finally:
            conn.close()

    def checkpoint_db(self):
        """Force database checkpointing to commit the WAL file changes."""
        logger.info("Executing SQLite database WAL checkpoint...")
        conn = self.get_connection()
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            logger.info("Database WAL checkpoint completed successfully.")
        except Exception as e:
            logger.error(f"Failed to checkpoint SQLite database: {e}")
        finally:
            conn.close()

db_manager = DatabaseManager()
