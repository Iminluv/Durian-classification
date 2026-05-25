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
def get_detections(limit: int = 50, offset: int = 0, batch_id: str = None):
    detections = db_manager.get_detections_history(limit=limit, offset=offset, batch_id=batch_id)
    return {"detections": detections, "limit": limit, "offset": offset}

# Benchmarks list CRUD
@router.get("/api/config/benchmarks")
def list_benchmarks():
    benchmarks_dir = Path("config/benchmarks")
    if not benchmarks_dir.exists():
        return []
    files = os.listdir(benchmarks_dir)
    return [f for f in files if f.endswith(".json")]

@router.get("/api/config/benchmarks/{name}")
def get_benchmark(name: str):
    benchmark_path = Path("config/benchmarks") / f"{name}.json"
    if not benchmark_path.exists():
        raise HTTPException(status_code=404, detail=f"Benchmark '{name}' not found.")
    try:
        with open(benchmark_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/config/benchmarks/{name}")
def save_benchmark(name: str, config: dict):
    benchmark_path = Path("config/benchmarks") / f"{name}.json"
    try:
        benchmark_path.parent.mkdir(parents=True, exist_ok=True)
        with open(benchmark_path, "w") as f:
            json.dump(config, f, indent=4)
        logger.info(f"Saved benchmark profile: {name}")
        return {"message": "Benchmark configuration saved successfully."}
    except Exception as e:
        logger.error(f"Error saving benchmark {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/config/benchmarks/{name}")
def delete_benchmark(name: str):
    benchmark_path = Path("config/benchmarks") / f"{name}.json"
    if not benchmark_path.exists():
        raise HTTPException(status_code=404, detail=f"Benchmark '{name}' not found.")
    try:
        os.remove(benchmark_path)
        logger.info(f"Deleted benchmark profile: {name}")
        return {"message": "Benchmark configuration deleted successfully."}
    except Exception as e:
        logger.error(f"Error deleting benchmark {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Config File Getters/Setters
@router.get("/api/config/rules")
def get_rules():
    rules_path = Path("config/rules.json")
    if not rules_path.exists():
        return {}
    with open(rules_path, "r") as f:
        return json.load(f)

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

@router.get("/api/config/camera")
def get_camera_config():
    camera_path = Path("config/camera.json")
    if not camera_path.exists():
        return {}
    with open(camera_path, "r") as f:
        return json.load(f)

@router.post("/api/config/camera")
def update_camera_config(config: dict):
    camera_path = Path("config/camera.json")
    try:
        camera_path.parent.mkdir(parents=True, exist_ok=True)
        with open(camera_path, "w") as f:
            json.dump(config, f, indent=4)
        logger.info("Updated camera.json configuration.")
        return {"message": "Camera configuration updated successfully."}
    except Exception as e:
        logger.error(f"Error updating camera config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/config/app")
def get_app_config():
    app_path = Path("config/app.json")
    if not app_path.exists():
        return {}
    with open(app_path, "r") as f:
        return json.load(f)

@router.post("/api/config/app")
def update_app_config(config: dict):
    app_path = Path("config/app.json")
    try:
        app_path.parent.mkdir(parents=True, exist_ok=True)
        with open(app_path, "w") as f:
            json.dump(config, f, indent=4)
        logger.info("Updated app.json configuration.")
        return {"message": "App configuration updated successfully."}
    except Exception as e:
        logger.error(f"Error updating app config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# OTA Updates API
@router.get("/api/model/update")
def get_model_update():
    pending_path = Path("config/pending_model.json")
    if not pending_path.exists():
        return {"status": "up_to_date"}
    try:
        with open(pending_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import shutil

@router.post("/api/model/update/approve")
def approve_model_update():
    pending_path = Path("config/pending_model.json")
    if not pending_path.exists():
        raise HTTPException(status_code=404, detail="No pending model update found.")
    
    try:
        with open(pending_path, "r") as f:
            pending_info = json.load(f)
            
        temp_model_dir = Path(pending_info["temp_model_dir"])
        
        # Resolve target model dir from app.json
        target_model_dir = Path("models/yolov26n_v1")
        app_path = Path("config/app.json")
        if app_path.exists():
            with open(app_path, "r") as f:
                app_cfg = json.load(f)
                target_model_dir = Path(app_cfg.get("model_dir", "models/yolov26n_v1"))
                
        if temp_model_dir.exists():
            target_model_dir.mkdir(parents=True, exist_ok=True)
            for item in os.listdir(temp_model_dir):
                s = temp_model_dir / item
                d = target_model_dir / item
                if s.is_dir():
                    if d.exists():
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            
            # Save metrics to evaluation_results.json
            with open("evaluation_results.json", "w") as f:
                json.dump(pending_info["new_metrics"], f, indent=4)
                
            # Clean up pending update temp folder
            shutil.rmtree(temp_model_dir)
            os.remove(pending_path)
            
            logger.info("Successfully approved and deployed OTA model update.")
            return {"status": "success", "message": "Model update successfully applied."}
        else:
            raise HTTPException(status_code=404, detail="Temporary model directory not found.")
            
    except Exception as e:
        logger.error(f"Error applying model update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/model/update/reject")
def reject_model_update():
    pending_path = Path("config/pending_model.json")
    if not pending_path.exists():
        raise HTTPException(status_code=404, detail="No pending model update found.")
    
    try:
        with open(pending_path, "r") as f:
            pending_info = json.load(f)
            
        temp_model_dir = Path(pending_info["temp_model_dir"])
        if temp_model_dir.exists():
            shutil.rmtree(temp_model_dir)
            
        os.remove(pending_path)
        logger.info("OTA model update rejected by operator.")
        return {"status": "success", "message": "Model update successfully rejected and cleared."}
        
    except Exception as e:
        logger.error(f"Error rejecting model update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import FileResponse
from reports.excel_report import generate_excel_report
from reports.pdf_report import generate_pdf_report

@router.get("/api/reports/{batch_id}/excel")
def download_excel_report(batch_id: str):
    logger.info(f"Excel report requested for batch: {batch_id}")
    file_path = generate_excel_report(batch_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Excel report could not be generated.")
    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/api/reports/{batch_id}/pdf")
def download_pdf_report(batch_id: str):
    logger.info(f"PDF report requested for batch: {batch_id}")
    file_path = generate_pdf_report(batch_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF report could not be generated.")
    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/pdf"
    )
