import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(title="Durian Classifier Workflow Runner API")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project root directory (assumed to be parent of workflow_app)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Global process tracker
current_process = None

# Class mapping (IDs to names in Roboflow)
CLASS_NAMES = ['crack', 'dark_spot', 'fungus', 'thorn_split']

class RunWorkflowRequest(BaseModel):
    mode: str
    image: Optional[str] = None
    n: Optional[int] = 5
    images_path: Optional[str] = "durian/test/images"
    labels_path: Optional[str] = "durian/test/labels"

def get_absolute_path(path_str: str) -> Path:
    """Helper to resolve paths relative to PROJECT_ROOT if not absolute, guarding against path traversal."""
    path = Path(path_str)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    resolved = path.resolve()
    # Guard against path traversal outside PROJECT_ROOT
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: Path traversal detected.")
    return resolved

@app.get("/api/config")
def get_config():
    """Get server configuration, including whether we are in cloud mode."""
    cloud_mode = os.environ.get("CLOUD_MODE", "false").lower() in ("true", "1", "yes")
    return {
        "cloud_mode": cloud_mode
    }

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload image files and optional label files."""
    print(f"[API Log] Received request to upload {len(files)} files.")
    images_dir = get_absolute_path("uploads/images")
    labels_dir = get_absolute_path("uploads/labels")
    
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_files = []
    
    for file in files:
        if not file.filename:
            continue
        
        filename = Path(file.filename).name  # Prevent directory traversal in filename
        file_ext = Path(filename).suffix.lower()
        
        if file_ext in [".jpg", ".jpeg", ".png"]:
            dest_path = images_dir / filename
            print(f"[API Log] Saving image: {filename} to {dest_path}")
            with open(dest_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            uploaded_files.append(filename)
            
            # Auto-generate empty label file if it does not exist
            label_filename = f"{Path(filename).stem}.txt"
            label_path = labels_dir / label_filename
            if not label_path.exists():
                print(f"[API Log] Auto-generating empty label file: {label_filename}")
                with open(label_path, "w") as lf:
                    pass
                    
        elif file_ext == ".txt":
            dest_path = labels_dir / filename
            print(f"[API Log] Saving label file: {filename} to {dest_path}")
            with open(dest_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            uploaded_files.append(filename)
            
    print(f"[API Log] Upload complete. Saved {len(uploaded_files)} files successfully.")
    return {"uploaded": uploaded_files, "count": len(uploaded_files)}

@app.delete("/api/uploads")
def clear_uploads():
    """Clear all files in the uploads/ directory."""
    print("[API Log] Request to clear all uploaded files.")
    images_dir = get_absolute_path("uploads/images")
    labels_dir = get_absolute_path("uploads/labels")
    
    deleted_count = 0
    for d in [images_dir, labels_dir]:
        if d.exists() and d.is_dir():
            for item in d.iterdir():
                if item.is_file():
                    item.unlink()
                    deleted_count += 1
    print(f"[API Log] Cleared uploads. Deleted {deleted_count} files.")
    return {"success": True, "deleted_count": deleted_count}

@app.get("/api/images")
def list_images(images_path: str = "durian/test/images"):
    """List all supported images in the specified directory."""
    print(f"[API Log] Listing images for path: {images_path}")
    abs_path = get_absolute_path(images_path)
    if not abs_path.exists() or not abs_path.is_dir():
        print(f"[API Log] Directory not found: {images_path}")
        raise HTTPException(status_code=404, detail=f"Images directory not found: {images_path}")
    
    images = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
        images.extend(p.name for p in abs_path.glob(ext))
    images.sort()
    print(f"[API Log] Found {len(images)} images in {images_path}")
    return {"images": images, "count": len(images)}

@app.get("/api/labels")
def get_labels(stem: str, labels_path: str = "durian/test/labels"):
    """Get the ground truth labels and bounding boxes for a specific image stem."""
    abs_path = get_absolute_path(labels_path)
    label_file = abs_path / f"{stem}.txt"
    
    if not label_file.exists():
        return {"expected_classes": [], "expected_boxes": []}
    
    try:
        expected_classes = []
        expected_boxes = []
        with open(label_file, "r") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                class_id = int(parts[0])
                if class_id < len(CLASS_NAMES):
                    cls_name = CLASS_NAMES[class_id]
                    expected_classes.append(cls_name)
                    
                    if len(parts) >= 5:
                        if len(parts) == 5:
                            # Standard YOLO bounding box
                            x_center = float(parts[1])
                            y_center = float(parts[2])
                            width = float(parts[3])
                            height = float(parts[4])
                        else:
                            # YOLO segmentation polygon format (N coordinate pairs: x1 y1 x2 y2 ...)
                            try:
                                x_coords = [float(x) for x in parts[1::2]]
                                y_coords = [float(y) for y in parts[2::2]]
                                if x_coords and y_coords:
                                    min_x = min(x_coords)
                                    max_x = max(x_coords)
                                    min_y = min(y_coords)
                                    max_y = max(y_coords)
                                    
                                    x_center = (min_x + max_x) / 2
                                    y_center = (min_y + max_y) / 2
                                    width = max_x - min_x
                                    height = max_y - min_y
                                else:
                                    continue
                            except ValueError:
                                continue
                                
                        expected_boxes.append({
                            "class": cls_name,
                            "x_center": x_center,
                            "y_center": y_center,
                            "width": width,
                            "height": height
                        })
        expected_classes = list(set(expected_classes))
        return {"expected_classes": expected_classes, "expected_boxes": expected_boxes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read label file: {str(e)}")

@app.get("/api/image")
def get_image(
    type: str = Query(..., pattern="^(original|annotated)$"),
    filename: str = Query(...),
    path: Optional[str] = "durian/test/images"
):
    """Serve an original or annotated image file."""
    if type == "original":
        img_dir = get_absolute_path(path)
        img_path = img_dir / filename
    else:
        # Annotated images are stored in output_images/
        img_dir = get_absolute_path("output_images")
        img_path = img_dir / f"annotated_{filename}"
        
        # Fallback in case the name already has annotated prefix or does not match
        if not img_path.exists():
            img_path = img_dir / filename

    if not img_path.exists():
        raise HTTPException(status_code=404, detail=f"Image {filename} ({type}) not found at {img_path}")
        
    return FileResponse(img_path)

@app.get("/api/results")
def get_results(results_file: str = "evaluation_results.json", labels_path: str = "durian/test/labels"):
    """Get the latest evaluation results JSON file, enriched with expected bounding boxes."""
    abs_path = get_absolute_path(results_file)
    if not abs_path.exists():
        return []
    
    try:
        with open(abs_path, "r") as f:
            results = json.load(f)
            
        # Enrich results with expected bounding boxes
        for r in results:
            img_name = r.get("image", "")
            stem = Path(img_name).stem
            labels_info = get_labels(stem, labels_path)
            r["expected_boxes"] = labels_info.get("expected_boxes", [])
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read results file: {str(e)}")

@app.post("/api/run")
def run_workflow(req: RunWorkflowRequest):
    """Reset outputs, configure environment, and spawn the workflow subprocess asynchronously."""
    global current_process
    
    # Check if a process is already running
    if current_process and current_process.poll() is None:
        raise HTTPException(status_code=400, detail="Workflow execution is already in progress.")
    
    # 1. Clean output directory (default: output_images)
    output_dir = get_absolute_path("output_images")
    if output_dir.exists():
        for item in output_dir.iterdir():
            if item.is_file():
                item.unlink()
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        
    # 2. Reset results file (default: evaluation_results.json)
    results_file = get_absolute_path("evaluation_results.json")
    if results_file.exists():
        results_file.unlink()
    
    # Write empty array so frontend gets a clean start
    with open(results_file, "w") as f:
        json.dump([], f)

    # 3. Construct subprocess command
    cmd = [sys.executable, str(PROJECT_ROOT / "run_workflow.py")]
    cmd.extend(["--mode", req.mode])
    if req.mode == "single" and req.image:
        cmd.extend(["--image", req.image])
    elif req.mode == "random_n" and req.n:
        cmd.extend(["--n", str(req.n)])

    # 4. Prepare environment variables (add PYTHONUNBUFFERED for real-time stdout logs)
    env = os.environ.copy()
    env["TEST_IMAGES"] = str(get_absolute_path(req.images_path))
    env["TEST_LABELS"] = str(get_absolute_path(req.labels_path))
    env["OUTPUT_DIR"] = str(output_dir)
    env["RESULTS_FILE"] = str(results_file)
    env["PYTHONUNBUFFERED"] = "1"

    # 5. Spawn the subprocess in background, redirecting output to workflow_run.log
    try:
        log_path = get_absolute_path("workflow_run.log")
        log_file = open(log_path, "w")
        
        print(f"Spawning background process: {' '.join(cmd)}")
        current_process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env,
            text=True
        )
        
        return {
            "success": True,
            "status": "started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")

@app.get("/api/status")
def get_status():
    """Check the status of the currently running background process."""
    global current_process
    if current_process is None:
        return {"status": "idle"}
        
    exit_code = current_process.poll()
    if exit_code is None:
        return {"status": "running"}
    elif exit_code == 0:
        return {"status": "completed"}
    else:
        # Read the end of the log to return the traceback/error message
        log_path = get_absolute_path("workflow_run.log")
        error_snippet = "Unknown error"
        if log_path.exists():
            try:
                with open(log_path, "r") as f:
                    content = f.read()
                    error_snippet = content[-1000:] if len(content) > 1000 else content
            except Exception:
                pass
        return {
            "status": "failed",
            "exit_code": exit_code,
            "error": error_snippet
        }

@app.get("/api/logs")
def get_logs():
    """Read the active running log file contents."""
    log_path = get_absolute_path("workflow_run.log")
    if not log_path.exists():
        return {"logs": "System ready. Waiting for execution..."}
        
    try:
        with open(log_path, "r") as f:
            return {"logs": f.read()}
    except Exception as e:
        return {"logs": f"Error reading logs: {str(e)}"}

# Mount static files directory
static_dir = PROJECT_ROOT / "workflow_app" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Defaulting to 8000 for standard local server
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
