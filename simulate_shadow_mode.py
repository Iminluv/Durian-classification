import os
import sys
import time
import json
import sqlite3
import random
import datetime
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.logger import logger
from core.database import db_manager
from core.vision_engine import VisionEngine
from core.rule_engine import RuleEngine
from core.relay_controller import RelayController

def run_shadow_simulation(num_fruits=20, delay=1.5):
    logger.info("Initializing Shadow Mode Simulation on edge device...")
    
    # Ensure config files exist
    rules_path = Path("config/rules.json")
    if not rules_path.exists():
        logger.error("rules.json configuration not found. Cannot run simulation.")
        return
        
    # Start a mock batch
    batch_id = f"SIM_SHADOW_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    operator_id = "sim_operator_01"
    
    logger.info(f"Starting simulated batch: {batch_id} (Operator: {operator_id})")
    db_manager.start_batch(batch_id, operator_id)
    
    # Initialize engines
    vision = VisionEngine("models/yolov26n_v1")
    rules = RuleEngine()
    relay = RelayController()
    
    # Track statistics
    stats = {
        "total": 0,
        "A": 0,
        "B": 0,
        "C": 0,
        "reject": 0
    }
    
    # List of mock defect distributions to simulate real conveyer belt
    fruit_scenarios = [
        # Clean Grade A
        {"name": "Clean Fruit 1", "detections": []},
        {"name": "Clean Fruit 2", "detections": []},
        {"name": "Clean Fruit 3", "detections": []},
        {"name": "Clean Fruit 4", "detections": []},
        {"name": "Clean Fruit 5", "detections": []},
        
        # Grade B (minor dark spots or splits)
        {"name": "Minor Dark Spot", "detections": [{"class": "dark_spot", "bbox": [100, 120, 30, 30], "confidence": 0.82}]},
        {"name": "Thorn Split Minor", "detections": [{"class": "thorn_split", "bbox": [200, 150, 40, 35], "confidence": 0.76}]},
        
        # Grade C (multiple minor defects or crack)
        {"name": "Minor Crack", "detections": [{"class": "crack", "bbox": [150, 200, 50, 20], "confidence": 0.88}]},
        {"name": "Split and Spot", "detections": [
            {"class": "thorn_split", "bbox": [80, 90, 35, 30], "confidence": 0.74},
            {"name": "Minor Spot", "class": "dark_spot", "bbox": [250, 280, 25, 25], "confidence": 0.69}
        ]},
        
        # Rejects (Fungus or multiple cracks or reject class)
        {"name": "Fungus Contaminated", "detections": [{"class": "fungus", "bbox": [180, 160, 45, 45], "confidence": 0.91}]},
        {"name": "Severe Crack Split", "detections": [
            {"class": "crack", "bbox": [120, 130, 90, 30], "confidence": 0.94},
            {"class": "reject", "bbox": [100, 100, 200, 200], "confidence": 0.89}
        ]},
        {"name": "Emergency Reject Class", "detections": [{"class": "reject", "bbox": [80, 100, 120, 120], "confidence": 0.85}]}
    ]

    print("\n" + "="*70)
    print(f" SHADOW MODE SIMULATOR - BATCH ID: {batch_id}")
    print("="*70)
    
    try:
        for i in range(1, num_fruits + 1):
            print(f"\n[Fruit #{i:02d}/{num_fruits:02d}] Passing conveyor sensor...")
            
            # Select random scenario
            scenario = random.choice(fruit_scenarios)
            detections = scenario["detections"]
            
            # Evaluate using active benchmark rules
            # Mock image dimensions 640x480
            w, h = 640, 480
            grade_result = rules.grade_fruit(detections, w, h)
            grade = grade_result["grade"]
            reasons = grade_result["reasons"]
            
            # Log to SQLite
            db_manager.add_detection(
                batch_id=batch_id,
                final_grade=grade,
                defect_types=[d["class"] for d in detections],
                defect_count=len(detections),
                confidence=float(sum(d["confidence"] for d in detections)/len(detections)) if detections else 1.0,
                image_path=f"simulated_frames/fruit_{i}.jpg",
                operator_id=operator_id
            )
            
            # Fire physical sorting relay
            relay.trigger(grade)
            
            # Update stats
            stats["total"] += 1
            stats[grade] += 1
            
            # Print details
            print(f"  Simulated defects: {', '.join([d['class'] for d in detections]) if detections else 'None (Clean)'}")
            print(f"  System Grade Decision: [GRADE {grade}]")
            if reasons:
                print(f"  Decision Reasons: {', '.join(reasons)}")
                
            time.sleep(delay)
            
    except KeyboardInterrupt:
        logger.warning("Simulation aborted by operator.")
    finally:
        db_manager.stop_batch(batch_id)
        logger.info(f"Simulation completed. Batch {batch_id} stopped.")
        
        # Display Final Summary
        print("\n" + "="*70)
        print(" SIMULATION SHADOW MODE REPORT SUMMARY")
        print("="*70)
        print(f"  Batch Session ID: {batch_id}")
        print(f"  Total Fruits Processed: {stats['total']}")
        print(f"  Grade A Count:   {stats['A']} ({stats['A']/max(1, stats['total'])*100:.1f}%)")
        print(f"  Grade B Count:   {stats['B']} ({stats['B']/max(1, stats['total'])*100:.1f}%)")
        print(f"  Grade C Count:   {stats['C']} ({stats['C']/max(1, stats['total'])*100:.1f}%)")
        print(f"  Reject Count:    {stats['reject']} ({stats['reject']/max(1, stats['total'])*100:.1f}%)")
        print("="*70)
        print("\n[INFO] Excel and PDF reports are now available for download.")
        print(f"To download Excel: GET http://127.0.0.1:8000/api/reports/{batch_id}/excel")
        print(f"To download PDF:   GET http://127.0.0.1:8000/api/reports/{batch_id}/pdf\n")

if __name__ == "__main__":
    count = 20
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            pass
    run_shadow_simulation(count)
