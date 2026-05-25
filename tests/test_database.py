import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.database import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_durian.db"
        self.db = DatabaseManager(db_path=str(self.db_path))

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_database_initialization(self):
        self.assertTrue(self.db_path.exists())
        # Check WAL mode enabled
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(mode.lower(), "wal")

    def test_batch_lifecycle(self):
        batch_id = "BATCH_2026_01"
        self.db.start_batch(batch_id, "operator_test")
        
        # Verify batch exists and start_time is set
        summary = self.db.get_batch_summary(batch_id)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["batch_id"], batch_id)
        self.assertIsNotNone(summary["start_time"])
        self.assertIsNone(summary["end_time"])

        self.db.stop_batch(batch_id)
        summary_stopped = self.db.get_batch_summary(batch_id)
        self.assertIsNotNone(summary_stopped["end_time"])

    def test_add_detections_aggregates(self):
        batch_id = "BATCH_SORT_02"
        self.db.start_batch(batch_id, "operator_test")

        # Add Grade A detection
        det_id_1 = self.db.add_detection(
            batch_id=batch_id,
            final_grade="A",
            defect_types=[],
            defect_count=0,
            confidence=1.0,
            image_path="A.jpg"
        )
        self.assertGreater(det_id_1, 0)

        # Add Reject detection
        det_id_2 = self.db.add_detection(
            batch_id=batch_id,
            final_grade="reject",
            defect_types=["fungus"],
            defect_count=1,
            confidence=0.88,
            image_path="R.jpg"
        )
        self.assertGreater(det_id_2, 0)

        # Verify batch stats are aggregated correctly
        summary = self.db.get_batch_summary(batch_id)
        self.assertEqual(summary["total_count"], 2)
        self.assertEqual(summary["grade_a"], 1)
        self.assertEqual(summary["reject"], 1)
        self.assertEqual(summary["grade_b"], 0)

        # Check detections history
        history = self.db.get_detections_history(limit=10)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["final_grade"], "reject")  # Ordered by desc timestamp
        self.assertEqual(history[1]["final_grade"], "A")

if __name__ == "__main__":
    unittest.main()
