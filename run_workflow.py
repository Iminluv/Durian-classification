import os
import json
import base64
import sys
import argparse
import random
import time
from pathlib import Path
from dotenv import load_dotenv
from inference_sdk import InferenceHTTPClient

# Class mapping (IDs to names in Roboflow)
CLASS_NAMES = ['crack', 'dark_spot', 'fungus', 'thorn_split']

# Inputs
TEST_IMAGES = os.environ.get("TEST_IMAGES", "durian/test/images")
TEST_LABELS = os.environ.get("TEST_LABELS", "durian/test/labels")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output_images")
RESULTS_FILE = os.environ.get("RESULTS_FILE", "evaluation_results.json")

def get_gt_classes_names(label_path):
    """Read ground truth classes from YOLO txt file and return as list of strings."""
    if not os.path.exists(label_path):
        return []
    with open(label_path) as f:
        class_ids = [int(line.split()[0]) for line in f.readlines()]
    # Return class names (removing duplicates)
    return list(set(CLASS_NAMES[cid] for cid in class_ids if cid < len(CLASS_NAMES)))

def extract_base64_string(data):
    """Recursively search for a base64 string in any nested dict/list/string structure."""
    if isinstance(data, str):
        cleaned = data.strip().replace("\n", "").replace("\r", "")
        # A base64 string for an image is typically long and doesn't contain spaces once cleaned.
        if len(cleaned) > 100 and " " not in cleaned:
            return cleaned
        return None
    if isinstance(data, dict):
        # Check standard keys first
        for key in ["value", "base64", "image"]:
            if key in data:
                res = extract_base64_string(data[key])
                if res:
                    return res
        # Fallback to searching all values
        for val in data.values():
            res = extract_base64_string(val)
            if res:
                return res
    if isinstance(data, list):
        for item in data:
            res = extract_base64_string(item)
            if res:
                return res
    return None

def run_workflow_evaluation():
    # Load API credentials from .env or environment
    load_dotenv()
    api_key = os.getenv("ROBOFLOW_API_KEY")
    workflow_id = os.getenv("ROBOFLOW_WORKFLOW_ID")
    
    if not api_key or not workflow_id:
        print("\n=== Roboflow Workflow Evaluator ===")
        if not api_key:
            api_key = input("Enter your Roboflow API Key: ").strip()
        if not workflow_id:
            workflow_id = input("Enter your Roboflow Workflow ID: ").strip()
        if not api_key or not workflow_id:
            print("Error: API Key and Workflow ID are required.")
            return

    workspace_name = "phongs-workspace-kigpq"
    
    print("\nInitializing Roboflow Inference Client...")
    client = InferenceHTTPClient(
        api_url="https://detect.roboflow.com",
        api_key=api_key
    )

    test_image_paths = list(Path(TEST_IMAGES).glob("*.jpg"))
    all_image_paths = test_image_paths
    
    if not all_image_paths:
        print(f"No JPG images found in {TEST_IMAGES}")
        return

    # Parse execution mode
    mode = "all"
    single_image_name = None
    num_n = 5

    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="Evaluate Roboflow Workflow for Durian Detection")
        parser.add_argument("--mode", choices=["all", "single", "random", "random_multi", "random_n"], default="all")
        parser.add_argument("--image", type=str, help="Specific image filename (required for 'single' mode)")
        parser.add_argument("--n", type=int, default=5, help="Number of images for 'random_n' mode")
        args = parser.parse_args()
        mode = args.mode
        single_image_name = args.image
        num_n = args.n
    else:
        # Interactive mode
        print("\n=== SELECT EXECUTION MODE ===")
        print("1. Evaluate all images (default)")
        print("2. Evaluate a specific image")
        print("3. Evaluate a random image for testing")
        print("4. Evaluate a random image with > 1 expected classes")
        print("5. Evaluate N random images")
        choice = input("Select an option (1-5) [Default: 1]: ").strip()
        if choice == "2":
            mode = "single"
            single_image_name = input("Enter the image filename (e.g. test_image_01.jpg): ").strip()
        elif choice == "3":
            mode = "random"
        elif choice == "4":
            mode = "random_multi"
        elif choice == "5":
            mode = "random_n"
            n_val = input("Enter the number of images to evaluate [Default: 5]: ").strip()
            if n_val.isdigit():
                num_n = int(n_val)
        else:
            mode = "all"

    # Select target images based on mode
    if mode == "random":
        image_paths = [random.choice(all_image_paths)]
        print(f"\n[Test Mode] Randomly selected image: {image_paths[0].name}")
    elif mode == "random_multi":
        # Filter images that have > 1 expected classes
        multi_class_images = []
        for p in all_image_paths:
            lbl_dir = TEST_LABELS
            lbl_path = Path(lbl_dir) / (p.stem + ".txt")
            expected = get_gt_classes_names(lbl_path)
            if len(expected) > 1:
                multi_class_images.append(p)
        
        if not multi_class_images:
            print("No images with > 1 expected classes found. Falling back to a standard random image.")
            image_paths = [random.choice(all_image_paths)]
        else:
            image_paths = [random.choice(multi_class_images)]
        print(f"\n[Test Mode] Randomly selected image with multiple classes: {image_paths[0].name}")
    elif mode == "random_n":
        sample_size = min(num_n, len(all_image_paths))
        image_paths = random.sample(all_image_paths, sample_size)
        print(f"\n[Test Mode] Randomly selected {sample_size} images")
    elif mode == "single":
        if not single_image_name:
            print("Error: Image filename must be specified for 'single' mode.")
            return
        matched = [p for p in all_image_paths if p.name == single_image_name or p.stem == single_image_name]
        if not matched:
            print(f"Error: Image '{single_image_name}' not found in {TEST_IMAGES}.")
            return
        image_paths = matched
        print(f"\n[Test Mode] Selected image: {image_paths[0].name}")
    else:
        image_paths = all_image_paths
        print(f"\nEvaluating all {len(image_paths)} images...")

    # Ensure output directory exists for annotated images
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("-" * 60)

    total = 0
    hits = 0
    results_summary = []

    for idx, img_path in enumerate(image_paths, 1):
        lbl_dir = TEST_LABELS
        label_path = Path(lbl_dir) / (img_path.stem + ".txt")
        expected = get_gt_classes_names(label_path)

        if not expected:
            # Skip unannotated images if any
            continue

        print(f"[{idx}/{len(image_paths)}] Processing: {img_path.name}")
        print(f"  Expected classes: {expected}")

        try:
            # Run the workflow and measure execution time
            start_time = time.perf_counter()
            res = client.run_workflow(
                workspace_name=workspace_name,
                workflow_id=workflow_id,
                images={"image": str(img_path)},
                parameters={"expected_classes": expected}
            )
            elapsed_time = time.perf_counter() - start_time

            # For debugging output image & predictions structure
            if idx == 1:
                try:
                    with open("debug_workflow_response.json", "w") as df:
                        json.dump(res, df, indent=2)
                    print(f"  [Debug] Saved raw workflow response to debug_workflow_response.json")
                except Exception as de:
                    print(f"  [Debug] Failed to save raw response: {de}")

            # Workflow output is a list containing results for each image in the batch
            if isinstance(res, list) and len(res) > 0:
                result_data = res[0]
            else:
                result_data = res

            # Extract outputs from workflow result
            hit = result_data.get("hit", False)
            missed = result_data.get("missed_classes", [])
            predictions = result_data.get("predictions", [])
            annotated_img_data = result_data.get("annotated_image")

            # Calculate hit classes (classes that were expected and not missed)
            hit_classes = list(set(expected) - set(missed))

            # Update count
            total += 1
            if hit:
                hits += 1

            # Print details
            print(f"  Hit: {hit}")
            print(f"  Hit Classes: {hit_classes}")
            if missed:
                print(f"  Missed Classes: {missed}")
            print(f"  API Runtime: {elapsed_time:.3f} seconds")
            
            # Resolve the predictions list
            predictions_list = []
            if isinstance(predictions, dict):
                if "predictions" in predictions:
                    predictions_list = predictions["predictions"]
                else:
                    for val in predictions.values():
                        if isinstance(val, list):
                            predictions_list = val
                            break
            elif isinstance(predictions, list):
                predictions_list = predictions

            # Format predictions for printing
            pred_list = []
            predictions_detailed = []
            for pred in predictions_list:
                if isinstance(pred, dict):
                    pred_class = pred.get('class')
                    pred_conf = pred.get('confidence')
                    # Keep confidence format safe (in case it is 0-100 or 0-1)
                    if pred_conf is not None:
                        if pred_conf > 1.0:
                            pred_conf = pred_conf / 100.0  # normalize to 0-1
                        pred_list.append(f"{pred_class} ({pred_conf:.2f})")
                    else:
                        pred_list.append(f"{pred_class} (N/A)")
                    
                    predictions_detailed.append({
                        "class": pred_class,
                        "confidence": pred_conf,
                        "x": pred.get("x"),
                        "y": pred.get("y"),
                        "width": pred.get("width"),
                        "height": pred.get("height")
                    })

            if pred_list:
                print(f"  Predictions: {', '.join(pred_list)}")
            else:
                print("  Predictions: None")

            # Save annotated image if present
            if annotated_img_data:
                b64_str = extract_base64_string(annotated_img_data)

                if b64_str:
                    # Strip any potential headers (e.g. data:image/jpeg;base64,)
                    if "," in b64_str:
                        b64_str = b64_str.split(",")[1]
                    
                    try:
                        img_bytes = base64.b64decode(b64_str)
                        output_path = Path(OUTPUT_DIR) / f"annotated_{img_path.name}"
                        output_path.write_bytes(img_bytes)
                        print(f"  Saved visualization: {output_path}")
                    except Exception as e:
                        print(f"  Failed to save annotated image: {e}")
                else:
                    print("  Warning: No base64 image data found in annotated_image payload.")
            else:
                print("  Warning: No annotated_image output returned by the workflow.")

            # Record detailed results
            new_result = {
                "image": img_path.name,
                "expected_classes": expected,
                "hit_classes": hit_classes,
                "missed_classes": missed,
                "hit": hit,
                "runtime_seconds": round(elapsed_time, 3),
                "predictions": predictions_detailed
            }
            results_summary.append(new_result)

            # Save intermediate results incrementally to support real-time UI tracking
            try:
                if mode in ["single", "random"] and os.path.exists(RESULTS_FILE):
                    existing_results = []
                    try:
                        with open(RESULTS_FILE, "r") as f:
                            existing_results = json.load(f)
                            if not isinstance(existing_results, list):
                                existing_results = []
                    except Exception:
                        pass
                    
                    # Merge current result
                    existing_results = [r for r in existing_results if r.get("image") != new_result["image"]]
                    existing_results.append(new_result)
                    
                    with open(RESULTS_FILE, "w") as f:
                        json.dump(existing_results, f, indent=2)
                else:
                    with open(RESULTS_FILE, "w") as f:
                        json.dump(results_summary, f, indent=2)
            except Exception as e:
                print(f"  Failed to save intermediate results: {e}")

        except Exception as e:
            import traceback
            print(f"  Error processing image: {e}")
            traceback.print_exc()
        
        print("-" * 60)

    # Summary
    if total > 0:
        avg_hit_rate = (hits / total) * 100
        avg_runtime = sum(r["runtime_seconds"] for r in results_summary) / len(results_summary)
        print("\n=== EVALUATION SUMMARY ===")
        print(f"Total Evaluated Images: {total}")
        print(f"Total Hits:             {hits}")
        print(f"Average Hit Rate:       {avg_hit_rate:.2f}%")
        print(f"Average Runtime:        {avg_runtime:.3f} seconds per image")
        print("==========================")
    else:
        print("\nNo images were successfully evaluated.")

if __name__ == "__main__":
    run_workflow_evaluation()
