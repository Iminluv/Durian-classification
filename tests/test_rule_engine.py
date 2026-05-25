import os
import sys
import unittest
import json
import tempfile
import shutil
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.rule_engine import RuleEngine

class TestRuleEngine(unittest.TestCase):
    def setUp(self):
        # Create temp folder for configs
        self.test_dir = tempfile.mkdtemp()
        self.rules_path = Path(self.test_dir) / "rules.json"
        self.benchmarks_dir = Path(self.test_dir) / "benchmarks"
        self.benchmarks_dir.mkdir(parents=True)
        
        # 1. Create a dummy benchmark file
        self.benchmark_data = {
            "name": "Test Benchmark v1",
            "created_by": "test",
            "created_at": "2026-05-25T10:00:00Z",
            "defect_rules": {
                "crack":       { "max_count_A": 0, "max_count_B": 0, "max_count_C": 1, "force_reject": False, "max_area_ratio": 0.02 },
                "dark_spot":   { "max_count_A": 0, "max_count_B": 1, "max_count_C": 2, "force_reject": False, "max_area_ratio": 0.05 },
                "fungus":      { "max_count_A": 0, "max_count_B": 0, "max_count_C": 0, "force_reject": True,  "max_area_ratio": 0.00 },
                "thorn_split": { "max_count_A": 0, "max_count_B": 1, "max_count_C": 2, "force_reject": False, "max_area_ratio": 0.08 },
                "reject":      { "max_count_A": 0, "max_count_B": 0, "max_count_C": 0, "force_reject": True,  "max_area_ratio": 0.00 }
            },
            "global_rules": {
                "max_total_defects_A": 0,
                "max_total_defects_B": 1,
                "max_total_defects_C": 3,
                "max_total_area_ratio_A": 0.00,
                "max_total_area_ratio_B": 0.03,
                "max_total_area_ratio_C": 0.08
            }
        }
        
        with open(self.benchmarks_dir / "test_benchmark.json", "w") as f:
            json.dump(self.benchmark_data, f)
            
        # 2. Create rules.json pointing to it
        self.rules_data = {
            "active_benchmark": "test_benchmark",
            "benchmarks_dir": str(self.benchmarks_dir),
            "confidence_thresholds": {}
        }
        with open(self.rules_path, "w") as f:
            json.dump(self.rules_data, f)

        self.engine = RuleEngine(rules_path=self.rules_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_grade_A_clean_fruit(self):
        # Empty detections -> Grade A
        res = self.engine.grade_fruit([], 640, 640)
        self.assertEqual(res["grade"], "A")
        self.assertEqual(sum(res["defect_counts"].values()), 0)

    def test_grade_B_one_defect(self):
        # One dark_spot (max_count_B is 1, A is 0) -> Grade B
        detections = [
            {"class": "dark_spot", "bbox": [100, 100, 20, 20], "confidence": 0.8} # Area ratio: 400 / 409600 = ~0.001
        ]
        res = self.engine.grade_fruit(detections, 640, 640)
        self.assertEqual(res["grade"], "B")

    def test_grade_C_defects(self):
        # One crack (max_count_C is 1, B is 0) -> Grade C
        detections = [
            {"class": "crack", "bbox": [100, 100, 15, 15], "confidence": 0.75}
        ]
        res = self.engine.grade_fruit(detections, 640, 640)
        self.assertEqual(res["grade"], "C")

    def test_immediate_reject_by_class(self):
        # One fungus detection (force_reject = True) -> Immediate reject
        detections = [
            {"class": "fungus", "bbox": [100, 100, 10, 10], "confidence": 0.8}
        ]
        res = self.engine.grade_fruit(detections, 640, 640)
        self.assertEqual(res["grade"], "reject")
        self.assertIn("Immediate reject forced by defect class 'fungus'", res["reasons"])

    def test_reject_by_exceeding_area(self):
        # Exceed max_area_ratio of dark_spot (limit: 0.05, 5% of 640x640 is 20480. Let's make bbox 300x100 = 30000)
        detections = [
            {"class": "dark_spot", "bbox": [100, 100, 300, 100], "confidence": 0.9}
        ]
        res = self.engine.grade_fruit(detections, 640, 640)
        self.assertEqual(res["grade"], "reject")
        self.assertTrue(any("area ratio" in r and "exceeded limit" in r for r in res["reasons"]))

if __name__ == "__main__":
    unittest.main()
