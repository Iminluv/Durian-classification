import os
import sys
import shutil
import cv2
import random
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import albumentations as A
from core.logger import logger

# Set random seed for reproducibility
random.seed(42)

class DatasetAugmenter:
    def __init__(self, input_dir, output_dir, multiplier=10):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.multiplier = multiplier

        # Define Albumentations augmentation pipeline
        self.transform = A.Compose([
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.5),
            A.RandomBrightnessContrast(p=0.3),
            A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.1, rotate_limit=30, p=0.5, border_mode=cv2.BORDER_CONSTANT, value=0),
            A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=15, val_shift_limit=10, p=0.3),
            A.GaussNoise(p=0.2),
            A.Blur(blur_limit=3, p=0.2),
        ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_visibility=0.3))

    def load_yolo_labels(self, label_path):
        bboxes = []
        class_labels = []
        if not label_path.exists():
            return bboxes, class_labels

        with open(label_path, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 5:
                    class_id = int(parts[0])
                    bbox = [float(x) for x in parts[1:]]
                    # YOLO format: [x_center, y_center, width, height]
                    # Limit values to [0, 1] to avoid out of bounds exceptions in Albumentations
                    bbox = [max(0.0, min(1.0, val)) for val in bbox]
                    bboxes.append(bbox)
                    class_labels.append(class_id)
        return bboxes, class_labels

    def save_yolo_labels(self, label_path, bboxes, class_labels):
        with open(label_path, "w") as f:
            for bbox, class_id in zip(bboxes, class_labels):
                f.write(f"{class_id} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}\n")

    def augment_split(self, split_name):
        logger.info(f"Processing split: {split_name}")
        src_img_dir = self.input_dir / split_name / "images"
        src_lbl_dir = self.input_dir / split_name / "labels"

        dest_img_dir = self.output_dir / split_name / "images"
        dest_lbl_dir = self.output_dir / split_name / "labels"

        dest_img_dir.mkdir(parents=True, exist_ok=True)
        dest_lbl_dir.mkdir(parents=True, exist_ok=True)

        if not src_img_dir.exists():
            logger.warning(f"Source image directory not found: {src_img_dir}")
            return

        image_files = list(src_img_dir.glob("*.jpg")) + list(src_img_dir.glob("*.png")) + list(src_img_dir.glob("*.jpeg"))
        
        for img_path in image_files:
            lbl_path = src_lbl_dir / (img_path.stem + ".txt")
            
            # Load image and labels
            image = cv2.imread(str(img_path))
            if image is None:
                logger.warning(f"Could not read image: {img_path}")
                continue

            bboxes, class_labels = self.load_yolo_labels(lbl_path)

            # Copy original to output
            dest_orig_img = dest_img_dir / img_path.name
            dest_orig_lbl = dest_lbl_dir / (img_path.stem + ".txt")
            shutil.copy(img_path, dest_orig_img)
            if lbl_path.exists():
                shutil.copy(lbl_path, dest_orig_lbl)

            # If not training split, we do not augment, only copy original
            if split_name != "train":
                continue

            # Run augmentations
            for i in range(self.multiplier):
                try:
                    augmented = self.transform(image=image, bboxes=bboxes, class_labels=class_labels)
                    aug_image = augmented['image']
                    aug_bboxes = augmented['bboxes']
                    aug_labels = augmented['class_labels']

                    # Save augmented image and labels
                    aug_stem = f"{img_path.stem}_aug_{i}"
                    aug_img_name = f"{aug_stem}{img_path.suffix}"
                    aug_lbl_name = f"{aug_stem}.txt"

                    cv2.imwrite(str(dest_img_dir / aug_img_name), aug_image)
                    self.save_yolo_labels(dest_lbl_dir / aug_lbl_name, aug_bboxes, aug_labels)
                except Exception as e:
                    logger.debug(f"Skipped one augmentation for {img_path.name} due to: {e}")
                    continue

        logger.info(f"Finished split: {split_name}")

    def run(self):
        logger.info(f"Starting augmentation. Input: {self.input_dir}, Output: {self.output_dir}")
        # Run train, val, test
        for split in ["train", "valid", "test"]:
            # Note: roboflow folder is valid, let's map it to val or support both
            split_folder = split
            if split == "valid" and not (self.input_dir / "valid").exists() and (self.input_dir / "val").exists():
                split_folder = "val"
            elif split == "val" and not (self.input_dir / "val").exists() and (self.input_dir / "valid").exists():
                split_folder = "valid"

            self.augment_split(split_folder)
            
        logger.info("Augmentation process complete.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Augment YOLO dataset using Albumentations")
    parser.add_argument("--input", default="durian", help="Input dataset directory")
    parser.add_argument("--output", default="data/augmented", help="Output dataset directory")
    parser.add_argument("--multiplier", type=int, default=10, help="Number of augmented images to generate per training image")
    args = parser.parse_args()

    augmenter = DatasetAugmenter(input_dir=args.input, output_dir=args.output, multiplier=args.multiplier)
    augmenter.run()
