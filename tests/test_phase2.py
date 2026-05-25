import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import shutil
import tempfile

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class TestPhase2Scripts(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.dummy_weights = Path(self.test_dir) / "dummy_best.pt"
        with open(self.dummy_weights, "w") as f:
            f.write("dummy weights content")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('train.mlflow')
    @patch('train.YOLO')
    @patch('torch.backends.mps.is_available', return_value=False)
    @patch('torch.cuda.is_available', return_value=False)
    def test_train_script_execution(self, mock_cuda, mock_mps, mock_yolo, mock_mlflow):
        # Import train_model function
        from train import train_model
        
        # Configure mock YOLO instance
        mock_model_instance = MagicMock()
        mock_yolo.return_value = mock_model_instance
        
        # Create output dir structure expected by script
        weights_dir = Path("runs/detect/train_durian/weights")
        weights_dir.mkdir(parents=True, exist_ok=True)
        best_pt = weights_dir / "best.pt"
        with open(best_pt, "w") as f:
            f.write("best weights")

        try:
            # Run train_model
            train_model(
                data_cfg="durian.yaml",
                epochs=1,
                imgsz=640,
                batch_size=8,
                device="cpu"
            )
            
            # Assertions
            mock_yolo.assert_called()
            mock_model_instance.train.assert_called_with(
                data="durian.yaml",
                epochs=1,
                imgsz=640,
                batch=8,
                device="cpu",
                project="runs/detect",
                name="train_durian",
                save=True,
                val=True,
                plots=True
            )
            mock_mlflow.set_experiment.assert_called_with("durian-defect-detection")
            self.assertTrue(os.path.exists("best.pt"))
        finally:
            # Clean up generated runs/ and best.pt
            if os.path.exists("best.pt"):
                os.remove("best.pt")
            if os.path.exists("runs"):
                shutil.rmtree("runs")

    @patch('export_model.YOLO')
    def test_export_script_execution(self, mock_yolo):
        from export_model import export_model
        
        # Configure mock YOLO and its export output paths
        mock_model_instance = MagicMock()
        # Mock export function returns string paths
        mock_model_instance.export.side_effect = lambda format, **kwargs: f"dummy_exported.{format}"
        mock_yolo.return_value = mock_model_instance

        # Create dummy exported files/dirs that the script expects to move
        Path("dummy_exported.onnx").touch()
        Path("dummy_exported.openvino").mkdir()
        Path("dummy_exported.coreml").mkdir()

        output_dir = Path(self.test_dir) / "exported_models"

        try:
            export_model(weights_path=str(self.dummy_weights), output_dir=str(output_dir))
            
            # Verify the files were moved to the output directory
            self.assertTrue((output_dir / "best.pt").exists())
            self.assertTrue((output_dir / "best.onnx").exists())
            self.assertTrue((output_dir / "openvino").exists())
            self.assertTrue((output_dir / "coreml").exists())
        finally:
            # Clean up any leftover files
            for p in ["dummy_exported.onnx", "dummy_exported.openvino", "dummy_exported.coreml"]:
                if os.path.exists(p):
                    if os.path.isdir(p):
                        shutil.rmtree(p)
                    else:
                        os.remove(p)

    @patch('evaluate.YOLO')
    def test_evaluate_script_execution(self, mock_yolo):
        from evaluate import evaluate_model
        
        # Mock val results
        mock_results = MagicMock()
        mock_results.box.map50 = 0.85
        mock_results.box.mr = 0.88
        mock_results.box.r = [0.90, 0.86, 0.87, 0.89, 0.91] # 5 classes
        
        mock_model_instance = MagicMock()
        mock_model_instance.val.return_value = mock_results
        mock_yolo.return_value = mock_model_instance

        try:
            results = evaluate_model(
                model_path=str(self.dummy_weights),
                data_cfg="durian.yaml",
                benchmark=False,
                runtime="pytorch"
            )
            
            # Assertions
            self.assertAlmostEqual(results["mAP50"], 0.85)
            self.assertAlmostEqual(results["recall_fungus"], 0.87) # class ID 2
            self.assertAlmostEqual(results["recall_reject"], 0.91) # class ID 4
            self.assertTrue(results["kpi_passed"])
            self.assertTrue(os.path.exists("evaluation_results.json"))
        finally:
            if os.path.exists("evaluation_results.json"):
                os.remove("evaluation_results.json")

if __name__ == "__main__":
    unittest.main()
