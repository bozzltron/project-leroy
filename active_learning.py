"""
Active Learning Module for Project Leroy
Collects non-bird detections (squirrels, cats, dogs, etc.) for future model training
"""
import os
import time
import logging
import cv2
from typing import Tuple
from utils import NON_BIRD_CLASSES

logger = logging.getLogger(__name__)


class ActiveLearningCollector:
    """
    Collects photos of non-bird detections (false positives) for active learning.
    These are used to refine the detection model over time.
    """

    def __init__(self, base_dir="storage/active_learning"):
        self.base_dir = base_dir
        self.non_birds_dir = os.path.join(base_dir, "non_birds")

        os.makedirs(self.non_birds_dir, exist_ok=True)

        self.non_bird_classes = NON_BIRD_CLASSES

    def collect_non_bird(self, frame: cv2.Mat, detected_class: str,
                         detection_score: float, bbox: Tuple[int, int, int, int],
                         visitation_id: str):
        """
        Collect photo when non-bird animal is detected.

        Args:
            frame: Full frame image
            detected_class: Detected class name (e.g., 'squirrel')
            detection_score: Detection confidence score
            bbox: Bounding box (x0, y0, x1, y1)
            visitation_id: Current visitation ID (if any)
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"nonbird_{detected_class}_{timestamp}_{visitation_id}_score{int(detection_score*100)}.png"
        filepath = os.path.join(self.non_birds_dir, filename)

        try:
            # Crop to bounding box with padding
            x0, y0, x1, y1 = bbox
            height, width = frame.shape[:2]
            padding = 20

            x0_padded = max(0, x0 - padding)
            y0_padded = max(0, y0 - padding)
            x1_padded = min(width, x1 + padding)
            y1_padded = min(height, y1 + padding)

            cropped = frame[y0_padded:y1_padded, x0_padded:x1_padded]
            cv2.imwrite(filepath, cropped)

            logger.info(f"Collected non-bird: {filename} ({detected_class})")
        except Exception as e:
            logger.error(f"Failed to save non-bird image: {e}")
