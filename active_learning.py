"""
Active Learning Module for Project Leroy
Handles collection of unknown birds, non-birds, and low-confidence detections
"""
import os
import time
import logging
import cv2
from typing import List, Tuple, Optional
from PIL import Image

logger = logging.getLogger(__name__)


class ActiveLearningCollector:
    """
    Collects photos for active learning:
    - Unknown birds (low confidence classifications)
    - Non-birds (squirrels, cats, etc.)
    - New species candidates
    """
    
    def __init__(self, base_dir="storage/active_learning"):
        self.base_dir = base_dir
        self.unknown_birds_dir = os.path.join(base_dir, "unknown_birds")
        self.non_birds_dir = os.path.join(base_dir, "non_birds")
        self.low_confidence_dir = os.path.join(base_dir, "low_confidence")
        self.new_species_dir = os.path.join(base_dir, "new_species_candidates")
        
        # Create directories
        for directory in [self.unknown_birds_dir, self.non_birds_dir, 
                         self.low_confidence_dir, self.new_species_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Non-bird classes to filter
        self.non_bird_classes = [
            'squirrel', 'cat', 'dog', 'rabbit', 'raccoon',
            'deer', 'fox', 'mouse', 'rat', 'chipmunk',
            'opossum', 'skunk', 'groundhog'
        ]
        
        # Statistics
        self.stats = {
            'unknown_birds': 0,
            'non_birds': 0,
            'low_confidence': 0,
            'new_species_candidates': 0
        }
    
    def categorize_detection(self, obj, labels, threshold=0.4) -> Tuple[str, Optional[str]]:
        """
        Categorize detection as bird, non-bird, or unknown.
        
        Returns:
            (category, label) tuple
            category: 'bird', 'non_bird', 'other', or 'unknown'
        """
        label = labels.get(obj.id, "").lower()
        score = obj.score
        
        if score < threshold:
            return "unknown", None
        
        # Bird class
        if label == 'bird':
            return "bird", "bird"
        
        # Non-bird animals (filter these out)
        if label in self.non_bird_classes:
            return "non_bird", label
        
        # Other objects (person, car, etc.) - ignore
        other_objects = ['person', 'car', 'truck', 'bicycle', 'motorcycle']
        if label in other_objects:
            return "other", label
        
        # Unknown - might be a bird we don't recognize
        return "unknown", label
    
    def collect_unknown_bird(self, image: Image.Image, detection_score: float, 
                           classification_results: List[Tuple[int, float]], 
                           labels: dict, visitation_id: str):
        """
        Collect photo when bird detected but species classification is uncertain.
        
        Args:
            image: PIL Image of the bird
            detection_score: Detection confidence score
            classification_results: List of (class_id, score) tuples from classification
            labels: Classification labels dictionary
            visitation_id: Current visitation ID
        """
        if not classification_results:
            return
        
        top_species_id, top_score = classification_results[0]
        top_species = labels.get(top_species_id, f"class_{top_species_id}")
        
        # Collect if confidence is low
        if top_score < 0.5:  # Low confidence threshold
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"unknown_{timestamp}_{visitation_id}_det{int(detection_score*100)}_cls{int(top_score*100)}_{top_species}.png"
            filepath = os.path.join(self.unknown_birds_dir, filename)
            
            try:
                image.save(filepath)
                self.stats['unknown_birds'] += 1
                logger.info(f"Collected unknown bird: {filename} (top: {top_species} @ {top_score:.2f})")
            except Exception as e:
                logger.error(f"Failed to save unknown bird image: {e}")
    
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
            
            self.stats['non_birds'] += 1
            logger.info(f"Collected non-bird: {filename} ({detected_class})")
        except Exception as e:
            logger.error(f"Failed to save non-bird image: {e}")
    
    def collect_low_confidence(self, image: Image.Image, detection_score: float,
                              classification_results: List[Tuple[int, float]],
                              labels: dict, visitation_id: str):
        """
        Collect photo when classification confidence is medium (50-80%).
        These might be correct but worth reviewing.
        """
        if not classification_results:
            return
        
        top_species_id, top_score = classification_results[0]
        top_species = labels.get(top_species_id, f"class_{top_species_id}")
        
        # Collect if confidence is medium (50-80%)
        if 0.5 <= top_score < 0.8:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"lowconf_{timestamp}_{visitation_id}_det{int(detection_score*100)}_cls{int(top_score*100)}_{top_species}.png"
            filepath = os.path.join(self.low_confidence_dir, filename)
            
            try:
                image.save(filepath)
                self.stats['low_confidence'] += 1
                logger.debug(f"Collected low confidence: {filename}")
            except Exception as e:
                logger.error(f"Failed to save low confidence image: {e}")
    
    def get_stats(self) -> dict:
        """Get collection statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'unknown_birds': 0,
            'non_birds': 0,
            'low_confidence': 0,
            'new_species_candidates': 0
        }

