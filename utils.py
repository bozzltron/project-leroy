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
    
    Args:
        path: Path to label file
        
    Returns:
        Dictionary mapping label IDs to label names
        
    Raises:
        FileNotFoundError: If label file doesn't exist
        ValueError: If label file format is invalid
    """
    p = re.compile(r'\s*(\d+)(.+)')
    labels = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f.readlines():
                match = p.match(line)
                if match:
                    num, text = match.groups()
                    labels[int(num)] = text.strip()
    except FileNotFoundError:
        logger.error(f"Label file not found: {path}")
        raise
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

