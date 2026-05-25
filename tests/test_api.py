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

if __name__ == "__main__":
    unittest.main()
