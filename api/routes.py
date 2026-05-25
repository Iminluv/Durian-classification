import os
import sys
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from core.logger import logger
from core.database import db_manager

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

router = APIRouter()

# Global state for active batch session
class ActiveSession:
    def __init__(self):
        self.active_batch_id = None
        self.operator_id = None

session_state = ActiveSession()

class StartBatchRequest(BaseModel):
    batch_id: str
    operator_id: str = None

class RuleConfigRequest(BaseModel):
    active_benchmark: str
    confidence_thresholds: dict

@router.get("/health")
def get_health():
    # Fetch model version, DB size, uptime, etc.
    db_size = 0
    if os.path.exists("data/durian.db"):
        db_size = os.path.getsize("data/durian.db")
        
    return {
        "status": "healthy",
        "model_version": "yolov26n_v1",
        "active_batch_id": session_state.active_batch_id,
        "database_size_bytes": db_size,
        "system_platform": sys.platform
    }

@router.post("/api/batch/start")
def start_batch(req: StartBatchRequest):
    if session_state.active_batch_id is not None:
        raise HTTPException(status_code=400, detail=f"Batch '{session_state.active_batch_id}' is already active.")
        
    success = db_manager.start_batch(req.batch_id, req.operator_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start batch in database.")
        
    session_state.active_batch_id = req.batch_id
    session_state.operator_id = req.operator_id
    return {"message": f"Batch '{req.batch_id}' started successfully.", "batch_id": req.batch_id}

@router.post("/api/batch/stop")
def stop_batch():
    if session_state.active_batch_id is None:
        raise HTTPException(status_code=400, detail="No active batch session running.")
        
    batch_id = session_state.active_batch_id
    success = db_manager.stop_batch(batch_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to stop batch in database.")
        
    session_state.active_batch_id = None
    session_state.operator_id = None
    return {"message": f"Batch '{batch_id}' stopped successfully.", "batch_id": batch_id}

@router.get("/api/batch/{batch_id}")
def get_batch(batch_id: str):
    summary = db_manager.get_batch_summary(batch_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")
    return summary

@router.get("/api/detections")
def get_detections(limit: int = 50, offset: int = 0):
    detections = db_manager.get_detections_history(limit=limit, offset=offset)
    return {"detections": detections, "limit": limit, "offset": offset}

@router.post("/api/config/rules")
def update_rules(req: RuleConfigRequest):
    rules_path = Path("config/rules.json")
    try:
        # Load existing
        rules = {}
        if rules_path.exists():
            with open(rules_path, "r") as f:
                rules = json.load(f)
                
        # Update
        rules["active_benchmark"] = req.active_benchmark
        rules["confidence_thresholds"] = req.confidence_thresholds
        
        # Save
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        with open(rules_path, "w") as f:
            json.dump(rules, f, indent=4)
            
        logger.info(f"Updated configuration file rules.json.")
        return {"message": "Rules configuration updated successfully."}
    except Exception as e:
        logger.error(f"Error updating rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Placeholder downloads for excel/pdf reporting (which will be implemented in Phase 4)
@router.get("/api/reports/{batch_id}/excel")
def download_excel_report(batch_id: str):
    logger.info(f"Excel report requested for batch: {batch_id}")
    return {"message": "Excel report generator stub.", "batch_id": batch_id}

@router.get("/api/reports/{batch_id}/pdf")
def download_pdf_report(batch_id: str):
    logger.info(f"PDF report requested for batch: {batch_id}")
    return {"message": "PDF report generator stub.", "batch_id": batch_id}
