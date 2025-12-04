"""
Photo capture and storage for Project Leroy
Uses UUID-based filenames with JSON metadata
"""
import cv2
import psutil
import os
import time 
import logging 
import threading
from typing import Optional, Tuple, List, Dict
from utils import clarity_from_image, is_focused
from photo_metadata import PhotoMetadata
from config import get_config

#Initialize logging files
logging.basicConfig(filename='storage/results.log',
                    format='%(asctime)s-%(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

# Backward compatibility: keep clarity() function for existing code
def clarity(image):
    """Backward compatibility wrapper for clarity_from_image."""
    return clarity_from_image(image)

def has_disk_space():
    hdd = psutil.disk_usage('/')
    return hdd.percent < 95

def capture(frame, visitation_id, detection_score, photo_type, 
            resolution: Optional[Tuple[int, int]] = None,
            detection_bbox: Optional[Tuple[int, int, int, int]] = None,
            classifications: Optional[List[Dict]] = None):
    """
    Capture and save photo with metadata.
    
    Args:
        frame: Image frame to save
        visitation_id: Visitation ID
        detection_score: Detection confidence score (0-1)
        photo_type: Type of photo (boxed, full)
        resolution: Optional (width, height) tuple
        detection_bbox: Optional bounding box (x0, y0, x1, y1)
        classifications: Optional list of classification results
    """
    thread = threading.Thread(
        target=save, 
        args=(frame, visitation_id, detection_score, photo_type, resolution, detection_bbox, classifications)
    )
    logger.info("Starting photo save thread")
    thread.start()

def mkdirs(visitation_id):
    directory = "storage/detected/{}/{}".format(time.strftime("%Y-%m-%d"), visitation_id)
    logger.info("Creating directories: {}".format(directory))
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory

def save(frame, visitation_id, detection_score, photo_type,
         resolution: Optional[Tuple[int, int]] = None,
         detection_bbox: Optional[Tuple[int, int, int, int]] = None,
         classifications: Optional[List[Dict]] = None):
    """Save photo with UUID filename and JSON metadata."""
    logger.info('Checking disk space')
    try:
        if not has_disk_space():
            logger.warning("Disk space low, skipping photo save")
            return
        
        directory = mkdirs(visitation_id)
        
        # Generate unique photo ID
        photo_id = PhotoMetadata.generate_photo_id()
        
        # Get resolution from frame if not provided
        if resolution is None:
            height, width = frame.shape[:2]
            resolution = (width, height)
        
        # Calculate clarity score
        clarity_score = clarity_from_image(frame)
        
        # Create metadata
        metadata = PhotoMetadata.create_metadata(
            photo_id=photo_id,
            visitation_id=visitation_id,
            photo_type=photo_type,
            resolution=resolution,
            detection_score=detection_score,
            detection_bbox=detection_bbox,
            classifications=classifications,
            clarity_score=clarity_score
        )
        
        # Generate filenames
        image_filename = PhotoMetadata.get_image_filename(photo_id, photo_type)
        metadata_filename = PhotoMetadata.get_metadata_filename(photo_id, photo_type)
        
        image_path = os.path.join(directory, image_filename)
        metadata_path = os.path.join(directory, metadata_filename)
        
        # Save image
        if not os.path.isfile(image_path):
            logger.info("Writing image: {}".format(image_path))
            cv2.imwrite(image_path, frame)
            
            # Save metadata
            if PhotoMetadata.save_metadata(metadata, metadata_path):
                logger.info("Saved metadata: {}".format(metadata_path))
            else:
                logger.warning("Failed to save metadata for {}".format(image_path))
        else:
            logger.warning("File already exists: {}".format(image_path))

    except Exception as e:
        logger.exception("Failed to save image: {}".format(e))