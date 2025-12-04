"""
Photo Metadata Management for Project Leroy
Handles UUID-based filenames with JSON metadata storage
"""
import json
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from pathlib import Path

logger = logging.getLogger(__name__)


class PhotoMetadata:
    """Manages photo metadata storage and retrieval."""
    
    @staticmethod
    def generate_photo_id() -> str:
        """Generate a unique photo ID (UUID)."""
        return str(uuid.uuid4())
    
    @staticmethod
    def get_image_filename(photo_id: str, photo_type: str = "boxed") -> str:
        """
        Generate image filename from photo ID.
        
        Args:
            photo_id: Unique photo identifier
            photo_type: Type of photo (boxed, full)
            
        Returns:
            Filename string
        """
        if photo_type == "full":
            return f"{photo_id}_full.png"
        return f"{photo_id}.png"
    
    @staticmethod
    def get_metadata_filename(photo_id: str, photo_type: str = "boxed") -> str:
        """
        Generate metadata filename from photo ID.
        
        Args:
            photo_id: Unique photo identifier
            photo_type: Type of photo (boxed, full)
            
        Returns:
            Metadata filename string
        """
        if photo_type == "full":
            return f"{photo_id}_full.json"
        return f"{photo_id}.json"
    
    @staticmethod
    def create_metadata(
        photo_id: str,
        visitation_id: str,
        photo_type: str,
        resolution: Tuple[int, int],
        detection_score: float,
        detection_bbox: Optional[Tuple[int, int, int, int]] = None,
        classifications: Optional[List[Dict]] = None,
        clarity_score: Optional[float] = None
    ) -> Dict:
        """
        Create metadata dictionary for a photo.
        
        Args:
            photo_id: Unique photo identifier
            visitation_id: Visitation ID this photo belongs to
            photo_type: Type of photo (boxed, full)
            resolution: (width, height) tuple
            detection_score: Detection confidence score (0-1)
            detection_bbox: Optional bounding box (x0, y0, x1, y1)
            classifications: Optional list of classification results
            clarity_score: Optional image clarity score
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "photo_id": photo_id,
            "visitation_id": visitation_id,
            "photo_type": photo_type,
            "resolution": {
                "width": resolution[0],
                "height": resolution[1]
            },
            "datetime": datetime.now().isoformat(),
            "detection": {
                "score": detection_score
            }
        }
        
        if detection_bbox:
            metadata["detection"]["bbox"] = {
                "x0": detection_bbox[0],
                "y0": detection_bbox[1],
                "x1": detection_bbox[2],
                "y1": detection_bbox[3]
            }
        
        if classifications:
            metadata["classifications"] = classifications
        
        if clarity_score is not None:
            metadata["clarity_score"] = clarity_score
        
        return metadata
    
    @staticmethod
    def save_metadata(metadata: Dict, filepath: str) -> bool:
        """
        Save metadata to JSON file.
        
        Args:
            metadata: Metadata dictionary
            filepath: Full path to save metadata file
            
        Returns:
            True if successful
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(metadata, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save metadata to {filepath}: {e}")
            return False
    
    @staticmethod
    def load_metadata(filepath: str) -> Optional[Dict]:
        """
        Load metadata from JSON file.
        
        Args:
            filepath: Path to metadata file
            
        Returns:
            Metadata dictionary or None if not found
        """
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to load metadata from {filepath}: {e}")
            return None
    
    @staticmethod
    def find_metadata_for_image(image_path: str) -> Optional[Dict]:
        """
        Find metadata file for an image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Metadata dictionary or None
        """
        # Try same directory with .json extension
        base_path = Path(image_path)
        metadata_path = base_path.with_suffix('.json')
        
        if metadata_path.exists():
            return PhotoMetadata.load_metadata(str(metadata_path))
        
        # Try with _full.json if it's a full image
        if '_full.png' in str(base_path):
            alt_path = base_path.with_name(base_path.stem.replace('_full', '') + '_full.json')
            if alt_path.exists():
                return PhotoMetadata.load_metadata(str(alt_path))
        
        return None

