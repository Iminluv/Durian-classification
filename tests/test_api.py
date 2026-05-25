import os
import sys
import unittest
from fastapi.testclient import TestClient
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from main import app
from api.routes import session_state

class TestFastAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Ensure session starts clean
        session_state.active_batch_id = None
        session_state.operator_id = None

    def tearDown(self):
        session_state.active_batch_id = None
        session_state.operator_id = None

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["model_version"], "yolov26n_v1")

    def test_batch_lifecycle_api(self):
        batch_id = "API_BATCH_TEST_01"
        
        # 1. Start Batch
        response = self.client.post("/api/batch/start", json={"batch_id": batch_id, "operator_id": "operator_api"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["batch_id"], batch_id)
        self.assertEqual(session_state.active_batch_id, batch_id)

        # 2. Start again should fail (400)
        response_dup = self.client.post("/api/batch/start", json={"batch_id": "ANOTHER_BATCH"})
        self.assertEqual(response_dup.status_code, 400)

        # 3. Stop Batch
        response_stop = self.client.post("/api/batch/stop")
        self.assertEqual(response_stop.status_code, 200)
        self.assertIsNone(session_state.active_batch_id)

        # 4. Stop again should fail (400)
        response_stop_dup = self.client.post("/api/batch/stop")
        self.assertEqual(response_stop_dup.status_code, 400)

    def test_detections_history_endpoint(self):
        response = self.client.get("/api/detections?limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("detections", data)
        self.assertEqual(data["limit"], 5)

    def test_report_generation(self):
        batch_id = "API_REPORT_BATCH"
        
        # Start batch so the record exists in SQLite
        self.client.post("/api/batch/start", json={"batch_id": batch_id, "operator_id": "operator_report"})
        
        # Test Excel download
        excel_res = self.client.get(f"/api/reports/{batch_id}/excel")
        self.assertEqual(excel_res.status_code, 200)
        self.assertEqual(excel_res.headers["content-type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        # Test PDF download
        pdf_res = self.client.get(f"/api/reports/{batch_id}/pdf")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.headers["content-type"], "application/pdf")
        
        # Stop batch
        self.client.post("/api/batch/stop")
        
        # Clean up any generated outputs
        excel_path = Path("reports/outputs") / f"batch_report_{batch_id}.xlsx"
        pdf_path = Path("reports/outputs") / f"batch_report_{batch_id}.pdf"
        if excel_path.exists():
            excel_path.unlink()
        if pdf_path.exists():
            pdf_path.unlink()

    def test_benchmark_crud_api(self):
        # Create
        bench_data = {
            "name": "Test Benchmark Profile",
            "defect_rules": {
                "crack": {"max_count_A": 0, "max_count_B": 1, "max_count_C": 2, "force_reject": False, "max_area_ratio": 0.05}
            }
        }
        res = self.client.post("/api/config/benchmarks/test_profile", json=bench_data)
        self.assertEqual(res.status_code, 200)
        
        # List
        res_list = self.client.get("/api/config/benchmarks")
        self.assertEqual(res_list.status_code, 200)
        self.assertIn("test_profile.json", res_list.json())
        
        # Get
        res_get = self.client.get("/api/config/benchmarks/test_profile")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["name"], "Test Benchmark Profile")
        
        # Delete
        res_del = self.client.delete("/api/config/benchmarks/test_profile")
        self.assertEqual(res_del.status_code, 200)
        
        # Get after delete should fail
        res_get_dup = self.client.get("/api/config/benchmarks/test_profile")
        self.assertEqual(res_get_dup.status_code, 404)

    def test_camera_and_app_config_api(self):
        # Camera
        cam_res = self.client.get("/api/config/camera")
        self.assertEqual(cam_res.status_code, 200)
        
        # App
        app_res = self.client.get("/api/config/app")
        self.assertEqual(app_res.status_code, 200)
        
    def test_ota_status_api(self):
        ota_res = self.client.get("/api/model/update")
        self.assertEqual(ota_res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
