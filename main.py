import os
import sys
import time
import base64
import cv2
import numpy as np
import asyncio
import threading
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from core.logger import logger
from core.database import db_manager
from core.db_backup import DBBackupService
from core.vision_engine import VisionEngine
from core.rule_engine import RuleEngine
from core.relay_controller import RelayController
from api.routes import router, session_state
from api.websocket import manager

# Add project root to sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

app = FastAPI(title="Automated Durian Classifier Backend")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(router)

# Global services references
backup_service = DBBackupService()
processing_task = None
loop_running = False
camera_cap = None
relay_ctrl = None

async def frame_processing_loop():
    global loop_running, camera_cap, relay_ctrl
    logger.info("Initializing engines for video processing loop...")
    
    # Import inside task to ensure everything is initialized
    from core.capture import CameraCapture
    
    capture = CameraCapture()
    vision = VisionEngine("models/yolov26n_v1")
    rules = RuleEngine()
    relay_ctrl = RelayController()
    
    last_grade_time = 0.0
    loop_running = True
    logger.info("Main processing loop successfully started.")

    try:
        while loop_running:
            # Maintain camera connection
            if not capture.cap or not capture.cap.isOpened():
                if not capture.initialize_camera():
                    logger.warning("Camera not initialized. Retrying in 2 seconds...")
                    await asyncio.sleep(2.0)
                    continue
            
            camera_cap = capture.cap
            ret, frame = capture.cap.read()
            if not ret:
                logger.warning("Failed to read frame. Sleeping...")
                await asyncio.sleep(0.2)
                continue
                
            # Run inference
            detections = vision.infer(frame)
            
            # Annotate frame
            annotated_frame = frame.copy()
            for det in detections:
                c_name = det["class"]
                bbox = det["bbox"]  # [x, y, w, h]
                conf = det["confidence"]
                
                # BGR Color scheme
                colors = {
                    "crack": (0, 165, 255),       # Orange
                    "dark_spot": (42, 42, 165),    # Brown
                    "fungus": (0, 255, 255),       # Yellow
                    "thorn_split": (0, 128, 255),  # Amber
                    "reject": (0, 0, 255)          # Red
                }
                color = colors.get(c_name, (255, 255, 255))
                
                cv2.rectangle(
                    annotated_frame, 
                    (bbox[0], bbox[1]), 
                    (bbox[0] + bbox[2], bbox[1] + bbox[3]), 
                    color, 
                    2
                )
                cv2.putText(
                    annotated_frame, 
                    f"{c_name} {conf:.2f}", 
                    (bbox[0], max(15, bbox[1] - 5)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, 
                    color, 
                    1
                )
                
            # Encode to base64 JPEG
            _, buffer = cv2.imencode('.jpg', annotated_frame)
            base64_frame = base64.b64encode(buffer).decode('utf-8')
            
            # Broadcast frame to UI live-feed client
            await manager.broadcast_live(base64_frame)
            
            # If batch is active, evaluate grading and triggers
            batch_id = session_state.active_batch_id
            if batch_id is not None:
                h, w = frame.shape[:2]
                grade_result = rules.grade_fruit(detections, w, h)
                grade = grade_result["grade"]
                reasons = grade_result["reasons"]
                
                now = time.time()
                # Run sorting grading evaluation if defects found, or every 3 seconds for clean fruit (Grade A)
                # This ensures we count/log every fruit going through, even if it has no defects
                should_log = False
                if len(detections) > 0 and (now - last_grade_time) >= 2.5:
                    should_log = True
                elif len(detections) == 0 and (now - last_grade_time) >= 4.0:
                    # Log Grade A fruit (clean)
                    should_log = True
                    grade = "A"
                    reasons = []

                if should_log:
                    # Trigger physical sorting relay
                    relay_ctrl.trigger(grade)
                    
                    # Log detection record to SQLite database
                    db_manager.add_detection(
                        batch_id=batch_id,
                        final_grade=grade,
                        defect_types=[d["class"] for d in detections],
                        defect_count=len(detections),
                        confidence=float(np.mean([d["confidence"] for d in detections])) if detections else 1.0,
                        image_path=None  # Can be mapped to saved raw frame
                    )
                    
                    # Broadcast sorting event to UI
                    event = {
                        "event_type": "detection",
                        "batch_id": batch_id,
                        "grade": grade,
                        "reasons": reasons,
                        "detections": detections,
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    await manager.broadcast_event(event)
                    last_grade_time = now
                    
            await asyncio.sleep(0.1)  # Limit process rate to 10 FPS
            
    except asyncio.CancelledError:
        logger.info("Processing loop cancelled.")
    except Exception as e:
        logger.error(f"Error in video processing loop: {e}")
    finally:
        capture.stop()
        logger.info("Camera resources released.")

@app.on_event("startup")
async def startup_event():
    global processing_task
    # Start SQLite WAL backups
    backup_service.start()
    
    # Spawn background video processing loop task
    processing_task = asyncio.create_task(frame_processing_loop())
    logger.info("Application startup actions complete.")

@app.on_event("shutdown")
async def shutdown_event():
    global loop_running, processing_task, relay_ctrl
    # Stop loop
    loop_running = False
    if processing_task:
        processing_task.cancel()
        
    # Stop backups
    backup_service.stop()
    
    # Commit WAL database logs
    db_manager.checkpoint_db()
    
    # Close USB Relay connection
    if relay_ctrl:
        relay_ctrl.close()
        
    logger.info("Application shutdown actions complete.")

# WebSockets routes integration
@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await manager.connect_live(websocket)
    try:
        while True:
            # Keep socket alive and receive any client messages
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_live(websocket)
    except Exception as e:
        logger.error(f"WebSocket live error: {e}")
        manager.disconnect_live(websocket)

@app.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket):
    await manager.connect_event(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_event(websocket)
    except Exception as e:
        logger.error(f"WebSocket event error: {e}")
        manager.disconnect_event(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
