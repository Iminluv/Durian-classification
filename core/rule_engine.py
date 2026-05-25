import os
import sys
import json
from pathlib import Path
from core.logger import logger

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class RuleEngine:
    def __init__(self, rules_path="config/rules.json"):
        self.rules_path = Path(rules_path)
        self.active_benchmark_name = "standard_qc_v1"
        self.benchmarks_dir = Path("config/benchmarks")
        
        self.rules_mtime = 0
        self.benchmark_mtime = 0
        
        self.benchmark_data = {}
        self.load_rules()

    def load_rules(self):
        """Loads configuration from rules.json and hot-reloads the active benchmark."""
        if not self.rules_path.exists():
            logger.warning(f"Rules config {self.rules_path} not found. Using defaults.")
            return

        try:
            mtime = self.rules_path.stat().st_mtime
            if mtime > self.rules_mtime:
                with open(self.rules_path, "r") as f:
                    data = json.load(f)
                self.active_benchmark_name = data.get("active_benchmark", "standard_qc_v1")
                self.benchmarks_dir = Path(data.get("benchmarks_dir", "config/benchmarks"))
                self.rules_mtime = mtime
                logger.info(f"Loaded rules.json. Active benchmark: {self.active_benchmark_name}")
                self.load_benchmark()
        except Exception as e:
            logger.error(f"Error loading rules config: {e}")

    def load_benchmark(self):
        """Loads the active benchmark JSON file."""
        benchmark_path = self.benchmarks_dir / f"{self.active_benchmark_name}.json"
        if not benchmark_path.exists():
            logger.error(f"Benchmark definition file not found at: {benchmark_path}")
            return

        try:
            mtime = benchmark_path.stat().st_mtime
            if mtime > self.benchmark_mtime:
                with open(benchmark_path, "r") as f:
                    self.benchmark_data = json.load(f)
                self.benchmark_mtime = mtime
                logger.info(f"Loaded active benchmark: '{self.benchmark_data.get('name')}'")
        except Exception as e:
            logger.error(f"Error loading benchmark: {e}")

    def check_updates(self):
        """Helper to check if configuration files have changed and hot-reload them."""
        self.load_rules()
        benchmark_path = self.benchmarks_dir / f"{self.active_benchmark_name}.json"
        if benchmark_path.exists():
            if benchmark_path.stat().st_mtime > self.benchmark_mtime:
                self.load_benchmark()

    def grade_fruit(self, detections: list[dict], frame_width: int, frame_height: int) -> dict:
        """
        Evaluate fruit detections against active benchmark.
        Returns:
            dict containing:
                "grade": str ("A", "B", "C", or "reject")
                "defect_counts": dict of class -> count
                "defect_areas": dict of class -> total area ratio
                "reasons": list of strings explaining why it was downgraded
        """
        # Ensure rules/benchmark are up-to-date
        self.check_updates()
        
        if not self.benchmark_data:
            logger.error("No active benchmark loaded. Grading everything as reject.")
            return {"grade": "reject", "defect_counts": {}, "defect_areas": {}, "reasons": ["No active benchmark loaded"]}

        defect_rules = self.benchmark_data.get("defect_rules", {})
        global_rules = self.benchmark_data.get("global_rules", {})
        
        frame_area = float(frame_width * frame_height)
        if frame_area <= 0:
            frame_area = 1.0  # Avoid division by zero
            
        defect_counts = {c: 0 for c in defect_rules.keys()}
        defect_areas = {c: 0.0 for c in defect_rules.keys()}
        reasons = []

        # 1. Parse and count detections
        total_defects = 0
        total_area_ratio = 0.0
        immediate_reject = False

        for det in detections:
            c_name = det.get("class")
            bbox = det.get("bbox")  # [x, y, w, h]
            
            if c_name not in defect_rules:
                # Unknown class -> flag for safety
                immediate_reject = True
                reasons.append(f"Detected unknown class '{c_name}'")
                continue

            rules = defect_rules[c_name]
            
            # Update counters
            defect_counts[c_name] += 1
            total_defects += 1
            
            # Calculate bbox area ratio
            if bbox and len(bbox) == 4:
                bbox_area = bbox[2] * bbox[3]
                area_ratio = bbox_area / frame_area
                defect_areas[c_name] += area_ratio
                total_area_ratio += area_ratio
            else:
                area_ratio = 0.0

            # Check class-specific rules
            if rules.get("force_reject", False):
                immediate_reject = True
                reasons.append(f"Immediate reject forced by defect class '{c_name}'")

            max_area_limit = rules.get("max_area_ratio", 0.0)
            if max_area_limit > 0 and area_ratio > max_area_limit:
                immediate_reject = True
                reasons.append(f"Defect '{c_name}' area ratio {area_ratio:.4f} exceeded limit {max_area_limit:.4f}")

        if immediate_reject:
            return {
                "grade": "reject",
                "defect_counts": defect_counts,
                "defect_areas": defect_areas,
                "reasons": reasons
            }

        # 2. Check Grade Levels (A -> B -> C -> Reject)
        
        # --- Grade A Check ---
        passed_A = True
        reasons_A = []
        for c_name, count in defect_counts.items():
            max_A = defect_rules[c_name].get("max_count_A", 0)
            if count > max_A:
                passed_A = False
                reasons_A.append(f"{c_name} count {count} > max_count_A ({max_A})")
                
        if total_defects > global_rules.get("max_total_defects_A", 0):
            passed_A = False
            reasons_A.append(f"Total defects {total_defects} > max_total_defects_A ({global_rules.get('max_total_defects_A')})")
            
        if total_area_ratio > global_rules.get("max_total_area_ratio_A", 0.0):
            passed_A = False
            reasons_A.append(f"Total area ratio {total_area_ratio:.4f} > max_total_area_ratio_A ({global_rules.get('max_total_area_ratio_A')})")

        if passed_A:
            return {"grade": "A", "defect_counts": defect_counts, "defect_areas": defect_areas, "reasons": []}

        # --- Grade B Check ---
        passed_B = True
        reasons_B = []
        for c_name, count in defect_counts.items():
            max_B = defect_rules[c_name].get("max_count_B", 0)
            if count > max_B:
                passed_B = False
                reasons_B.append(f"{c_name} count {count} > max_count_B ({max_B})")
                
        if total_defects > global_rules.get("max_total_defects_B", 0):
            passed_B = False
            reasons_B.append(f"Total defects {total_defects} > max_total_defects_B ({global_rules.get('max_total_defects_B')})")
            
        if total_area_ratio > global_rules.get("max_total_area_ratio_B", 0.0):
            passed_B = False
            reasons_B.append(f"Total area ratio {total_area_ratio:.4f} > max_total_area_ratio_B ({global_rules.get('max_total_area_ratio_B')})")

        if passed_B:
            return {"grade": "B", "defect_counts": defect_counts, "defect_areas": defect_areas, "reasons": reasons_A}

        # --- Grade C Check ---
        passed_C = True
        reasons_C = []
        for c_name, count in defect_counts.items():
            max_C = defect_rules[c_name].get("max_count_C", 0)
            if count > max_C:
                passed_C = False
                reasons_C.append(f"{c_name} count {count} > max_count_C ({max_C})")
                
        if total_defects > global_rules.get("max_total_defects_C", 0):
            passed_C = False
            reasons_C.append(f"Total defects {total_defects} > max_total_defects_C ({global_rules.get('max_total_defects_C')})")
            
        if total_area_ratio > global_rules.get("max_total_area_ratio_C", 0.0):
            passed_C = False
            reasons_C.append(f"Total area ratio {total_area_ratio:.4f} > max_total_area_ratio_C ({global_rules.get('max_total_area_ratio_C')})")

        if passed_C:
            return {"grade": "C", "defect_counts": defect_counts, "defect_areas": defect_areas, "reasons": reasons_B}

        # --- Reject ---
        all_reasons = reasons_C
        all_reasons.append("Failed to satisfy Grade C requirements")
        return {
            "grade": "reject",
            "defect_counts": defect_counts,
            "defect_areas": defect_areas,
            "reasons": all_reasons
        }
