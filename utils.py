"""
Shared utility functions for Project Leroy
Consolidates common functionality to avoid duplication
"""
import re
import cv2
import logging
import numpy as np
from typing import Dict

logger = logging.getLogger(__name__)

# COCO 80 only has cat (class 16) and dog (class 17) as small mammals.
# Other animals (squirrel, rabbit, etc.) are NOT in COCO 80.
# These non-bird detections are logged for future model training.
NON_BIRD_CLASSES = ['cat', 'dog']

def load_labels(path: str) -> Dict[int, str]:
    """
    Load label file and return as dictionary.
    
    Supports two formats:
    1. Text format: "ID label" (e.g., "16 bird")
    2. JSON format: {"0": "person", "1": "bicycle", ...} (Hailo Model Zoo format)
    
    Args:
        path: Path to label file (.txt or .json)
        
    Returns:
        Dictionary mapping label IDs to label names
        
    Raises:
        FileNotFoundError: If label file doesn't exist
        ValueError: If label file format is invalid
    """
    labels = {}
    try:
        # Try JSON format first (Hailo Model Zoo format)
        if path.endswith('.json'):
            import json
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle both {"0": "label"} and {"labels": ["label0", "label1"]} formats
                if isinstance(data, dict):
                    if "labels" in data:
                        # Format: {"labels": ["person", "bicycle", ...]}
                        for idx, label in enumerate(data["labels"]):
                            labels[idx] = str(label)
                    else:
                        # Format: {"0": "person", "1": "bicycle", ...}
                        for key, value in data.items():
                            try:
                                labels[int(key)] = str(value)
                            except (ValueError, TypeError):
                                continue
                elif isinstance(data, list):
                    # Format: ["person", "bicycle", ...]
                    for idx, label in enumerate(data):
                        labels[idx] = str(label)
        else:
            # Text format. Try "ID label" first (e.g., "16 bird"),
            # then fall back to one-label-per-line with line number as ID.
            p = re.compile(r'\s*(\d+)(.+)')
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for idx, line in enumerate(lines):
                match = p.match(line)
                if match:
                    num, text = match.groups()
                    labels[int(num)] = text.strip()
            if not labels and lines:
                # Fallback: one label per line, line number (0-indexed) is the ID
                logger.info(
                    f"No 'ID label' format found in {path}; "
                    f"using line number as ID (Hailo Model Zoo format)"
                )
                for idx, line in enumerate(lines):
                    label = line.strip()
                    if label:
                        labels[idx] = label
    except FileNotFoundError:
        raise FileNotFoundError(f"Labels not found: {path}")
    except Exception as e:
        logger.error(f"Failed to load labels from {path}: {e}")
        raise
    return labels


def clarity_from_image(image: np.ndarray) -> float:
    """
    Compute image clarity (focus measure) from numpy array.
    
    Uses Laplacian variance - higher values indicate sharper images.
    
    Args:
        image: Image as numpy array (BGR format from OpenCV)
        
    Returns:
        Clarity score (variance of Laplacian)
    """
    if image is None:
        return 0.0
    
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except Exception as e:
        logger.warning(f"Error computing clarity from image: {e}")
        return 0.0


def clarity_from_path(image_path: str) -> float:
    """
    Compute image clarity (focus measure) from file path.
    
    Uses Laplacian variance - higher values indicate sharper images.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Clarity score (variance of Laplacian)
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            logger.warning(f"Could not read image: {image_path}")
            return 0.0
        return clarity_from_image(image)
    except Exception as e:
        logger.warning(f"Error computing clarity from path {image_path}: {e}")
        return 0.0

