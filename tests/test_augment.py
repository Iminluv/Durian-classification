import os
import sys
import unittest
import shutil
import tempfile
from pathlib import Path
import cv2
import numpy as np

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.augment import DatasetAugmenter

class TestDatasetAugmenter(unittest.TestCase):
    def setUp(self):
        # Create temp directories for testing
        self.test_dir = tempfile.mkdtemp()
        self.input_dir = Path(self.test_dir) / "input"
        self.output_dir = Path(self.test_dir) / "output"
        self.input_dir.mkdir()
        self.output_dir.mkdir()

        # Create subfolders for train, valid, test
        for split in ["train", "valid", "test"]:
            (self.input_dir / split / "images").mkdir(parents=True)
            (self.input_dir / split / "labels").mkdir(parents=True)

        # Create dummy image and label file
        self.dummy_img_path = self.input_dir / "train" / "images" / "dummy.jpg"
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(str(self.dummy_img_path), dummy_img)

        self.dummy_lbl_path = self.input_dir / "train" / "labels" / "dummy.txt"
        with open(self.dummy_lbl_path, "w") as f:
            f.write("0 0.5 0.5 0.2 0.2\n")

    def tearDown(self):
        # Clean up temp directories
        shutil.rmtree(self.test_dir)

    def test_load_save_yolo_labels(self):
        augmenter = DatasetAugmenter(self.input_dir, self.output_dir)
        bboxes, labels = augmenter.load_yolo_labels(self.dummy_lbl_path)
        
        self.assertEqual(len(bboxes), 1)
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0], 0)
        self.assertAlmostEqual(bboxes[0][0], 0.5)

        # Test save
        out_lbl_path = Path(self.test_dir) / "out.txt"
        augmenter.save_yolo_labels(out_lbl_path, bboxes, labels)
        
        bboxes_new, labels_new = augmenter.load_yolo_labels(out_lbl_path)
        self.assertEqual(len(bboxes_new), 1)
        self.assertEqual(labels_new[0], 0)
        self.assertAlmostEqual(bboxes_new[0][0], 0.5)

    def test_augmentation_train_split(self):
        # Set multiplier to 2
        augmenter = DatasetAugmenter(self.input_dir, self.output_dir, multiplier=2)
        augmenter.augment_split("train")

        # Expect original + 2 augmented versions = 3 images/labels total
        dest_img_dir = self.output_dir / "train" / "images"
        dest_lbl_dir = self.output_dir / "train" / "labels"

        images = list(dest_img_dir.glob("*.jpg"))
        labels = list(dest_lbl_dir.glob("*.txt"))

        self.assertEqual(len(images), 3)
        self.assertEqual(len(labels), 3)

        # Check filenames contain _aug_0 and _aug_1
        filenames = [img.name for img in images]
        self.assertIn("dummy.jpg", filenames)
        self.assertIn("dummy_aug_0.jpg", filenames)
        self.assertIn("dummy_aug_1.jpg", filenames)

    def test_validation_split_not_augmented(self):
        # Put a dummy in valid
        valid_img_path = self.input_dir / "valid" / "images" / "valid_dummy.jpg"
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(str(valid_img_path), dummy_img)

        valid_lbl_path = self.input_dir / "valid" / "labels" / "valid_dummy.txt"
        with open(valid_lbl_path, "w") as f:
            f.write("1 0.3 0.3 0.1 0.1\n")

        augmenter = DatasetAugmenter(self.input_dir, self.output_dir, multiplier=5)
        augmenter.augment_split("valid")

        # Expect exactly 1 image and label in output (no augmentation)
        dest_img_dir = self.output_dir / "valid" / "images"
        dest_lbl_dir = self.output_dir / "valid" / "labels"

        images = list(dest_img_dir.glob("*.jpg"))
        labels = list(dest_lbl_dir.glob("*.txt"))

        self.assertEqual(len(images), 1)
        self.assertEqual(len(labels), 1)
        self.assertEqual(images[0].name, "valid_dummy.jpg")

if __name__ == "__main__":
    unittest.main()
