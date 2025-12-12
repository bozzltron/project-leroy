"""
Shared utility functions for Project Leroy
Consolidates common functionality to avoid duplication
"""
import re
import cv2
import logging
import numpy as np
from typing import Dict, Union

logger = logging.getLogger(__name__)


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
            # Try text format: "ID label"
            p = re.compile(r'\s*(\d+)(.+)')
            with open(path, 'r', encoding='utf-8') as f:
                for line in f.readlines():
                    match = p.match(line)
                    if match:
                        num, text = match.groups()
                        labels[int(num)] = text.strip()
    except FileNotFoundError:
        # Provide helpful error message with suggestions
        import os
        model_dir = os.path.dirname(path) if os.path.dirname(path) else 'all_models'
        available_files = []
        if os.path.exists(model_dir):
            available_files = [f for f in os.listdir(model_dir) if f.endswith('.txt')]
        
        error_msg = (
            f"Label file not found: {path}\n"
            f"\n"
        )
        if available_files:
            error_msg += (
                f"Found text files in {model_dir}:\n"
            )
            for f in available_files:
                error_msg += f"  - {f}\n"
            error_msg += (
                f"\n"
                f"Tip: If you have a labels file with a different name, you can:\n"
                f"  1. Rename it to coco_labels.txt (for COCO models)\n"
                f"  2. Or use --labels flag: python leroy.py --labels /path/to/your_labels.txt\n"
                f"\n"
            )
        else:
            error_msg += (
                f"No label files found in {model_dir}\n"
                f"\n"
                f"SOLUTION:\n"
                f"1. Download labels file from model documentation or Model Zoo\n"
                f"2. For COCO models: coco_labels.txt (80 classes)\n"
                f"3. For iNaturalist: inat_bird_labels.txt (bird species)\n"
                f"4. Place in: {model_dir}/\n"
                f"\n"
            )
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
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


def is_focused(image: Union[np.ndarray, str], threshold: float = 100.0) -> bool:
    """
    Check if image is in focus.
    
    Args:
        image: Image as numpy array or file path
        threshold: Minimum clarity score to be considered focused
        
    Returns:
        True if image clarity exceeds threshold
    """
    if isinstance(image, str):
        clarity_score = clarity_from_path(image)
    else:
        clarity_score = clarity_from_image(image)
    
    return clarity_score > threshold

