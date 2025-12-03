#!/usr/bin/env python3
"""
Project Leroy - Bird Detection System
Raspberry Pi 5 + AI Kit (Hailo) Implementation

Dual-Resolution Strategy:
- Detection: 5MP (2048x1536) for fast processing
- Photos: 12MP (4056x3040) for high-quality captures when bird detected
"""
import argparse
import collections
import cv2
import os
import sys
import numpy as np
import re
import logging
import imutils
import time
import signal
from PIL import Image
from visitations import Visitations
from hailo_inference import HailoInference
from camera_manager import CameraManager
from active_learning import ActiveLearningCollector

print("OpenCV version: " + cv2.__version__)

Object = collections.namedtuple('Object', ['id', 'score', 'bbox'])

# Initialize logging
logging.basicConfig(
    filename='storage/results.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


def load_labels(path):
    """Load label file and return as dictionary."""
    p = re.compile(r'\s*(\d+)(.+)')
    labels = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f.readlines():
                match = p.match(line)
                if match:
                    num, text = match.groups()
                    labels[int(num)] = text.strip()
    except Exception as e:
        logger.error(f"Failed to load labels from {path}: {e}")
        raise
    return labels


class BBox(collections.namedtuple('BBox', ['xmin', 'ymin', 'xmax', 'ymax'])):
    """Bounding box.
    Represents a rectangle which sides are either vertical or horizontal, parallel
    to the x or y axis.
    """
    __slots__ = ()


def has_bird_detection(objs, labels, threshold=0.4):
    """Check if any detection is a bird above threshold."""
    for obj in objs:
        label = labels.get(obj.id, "")
        if label.lower() == 'bird' and obj.score >= threshold:
            return True
    return False


def filter_and_categorize_detections(objs, labels, threshold=0.4):
    """
    Filter detections into birds, non-birds, and others.
    
    Returns:
        (birds, non_birds, others) tuple of Object lists
    """
    birds = []
    non_birds = []
    others = []
    
    non_bird_classes = [
        'squirrel', 'cat', 'dog', 'rabbit', 'raccoon',
        'deer', 'fox', 'mouse', 'rat', 'chipmunk',
        'opossum', 'skunk', 'groundhog'
    ]
    
    for obj in objs:
        label = labels.get(obj.id, "").lower()
        score = obj.score
        
        if score < threshold:
            continue
        
        if label == 'bird':
            birds.append(obj)
        elif label in non_bird_classes:
            non_birds.append(obj)
        else:
            others.append(obj)
    
    return birds, non_birds, others


def convert_detections(detections, frame_shape):
    """Convert Hailo detections to Object format."""
    objs = []
    for det in detections:
        obj = Object(
            id=det['id'],
            score=det['score'],
            bbox=BBox(
                xmin=det['bbox']['xmin'],
                ymin=det['bbox']['ymin'],
                xmax=det['bbox']['xmax'],
                ymax=det['bbox']['ymax']
            )
        )
        objs.append(obj)
    return objs


def main():
    """Main detection loop with dual-resolution strategy."""
    camera = None
    hailo = None
    
    # Signal handler for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal (SIGTERM/SIGINT), cleaning up...")
        # Cleanup will happen in finally block
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        default_model_dir = 'all_models'
        default_model = 'ssd_mobilenet_v2_coco.hef'  # HEF format
        default_labels = 'coco_labels.txt'
        
        parser = argparse.ArgumentParser(
            description='Project Leroy - Bird Detection with Hailo AI Kit'
        )
        parser.add_argument(
            '--model',
            help='HEF model path',
            default=os.path.join(default_model_dir, default_model)
        )
        parser.add_argument(
            '--labels',
            help='Label file path',
            default=os.path.join(default_model_dir, default_labels)
        )
        parser.add_argument(
            '--top_k',
            type=int,
            default=3,
            help='Number of categories with highest score to display'
        )
        parser.add_argument(
            '--camera_idx',
            type=int,
            help='Index of which video source to use (0 for HQ Camera)',
            default=0
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.1,
            help='Classifier score threshold'
        )
        parser.add_argument(
            '--detection-width',
            type=int,
            default=500,
            help='Width for detection resizing (default: 500px)'
        )
        args = parser.parse_args()

        logger.info(f"Starting Project Leroy detection system")
        logger.info(f"Model: {args.model}, Labels: {args.labels}")
        logger.info("Dual-resolution strategy: 1.2MP detection (resized to 500px), 12MP photos")

        # Initialize Hailo inference
        logger.info("Initializing Hailo AI Kit...")
        hailo = HailoInference()
        hailo.initialize()
        hailo.load_detection_model(args.model)
        
        # Load labels
        labels = load_labels(args.labels)
        logger.info(f"Loaded {len(labels)} labels")

        # Initialize camera manager (starts at 5MP for detection)
        logger.info(f"Initializing camera (index {args.camera_idx})...")
        camera = CameraManager(camera_idx=args.camera_idx)
        if not camera.initialize():
            raise RuntimeError(f"Failed to initialize camera {args.camera_idx}")

        # Initialize visitation tracking
        logger.info("Initializing visitation tracking...")
        visitations = Visitations()
        
        # Initialize active learning collector
        logger.info("Initializing active learning collector...")
        active_learning = ActiveLearningCollector()

        logger.info("Starting detection loop at 1.2MP (resized to 500px for inference, 12MP photos when bird detected)...")
        frame_count = 0
        last_photo_time = 0
        photo_cooldown = 0.5  # Minimum seconds between high-res captures

        while True:
            try:
                # Get detection frame (5MP)
                ret, frame = camera.get_detection_frame()
                if not ret:
                    time.sleep(0.1)  # Brief pause before retry
                    continue

                frame_count += 1

                # Resize frame for detection (maintain aspect ratio)
                resized_frame = imutils.resize(frame, width=args.detection_width)
                pil_image = Image.fromarray(cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB))

                # Run detection inference
                detections = hailo.detect(
                    pil_image,
                    score_threshold=args.threshold,
                    top_k=args.top_k
                )

                # Clean up PIL image immediately
                pil_image.close()

                # Convert Hailo detections to Object format
                objs = convert_detections(detections, frame.shape)

                # Filter and categorize detections (birds, non-birds, others)
                bird_objs, non_bird_objs, other_objs = filter_and_categorize_detections(
                    objs, labels, threshold=0.4
                )
                
                # Log non-bird detections (for learning)
                if non_bird_objs:
                    for obj in non_bird_objs:
                        label = labels.get(obj.id, "")
                        logger.info(f"Non-bird detected: {label} (score: {obj.score:.2f})")
                        # Collect non-bird for learning
                        height, width = frame.shape[:2]
                        bbox = (
                            int(obj.bbox.xmin * width),
                            int(obj.bbox.ymin * height),
                            int(obj.bbox.xmax * width),
                            int(obj.bbox.ymax * height)
                        )
                        active_learning.collect_non_bird(
                            frame, label, obj.score, bbox, 
                            visitations.visitation_id or "unknown"
                        )
                
                # Check if bird detected
                bird_detected = len(bird_objs) > 0
                
                # Update visitations with bird detections only
                # This handles visitation tracking and saves boxed photos from detection frame
                visitations.update(bird_objs, frame, labels)

                # If bird detected and enough time has passed, capture high-res photo
                if bird_detected:
                    current_time = time.time()
                    if (current_time - last_photo_time >= photo_cooldown and 
                        not camera.is_photo_capture_pending()):
                        
                        # Capture high-resolution photo in background
                        # Store current detections for use in callback
                        current_objs = objs.copy()
                        current_frame = frame.copy()
                        
                        def handle_high_res_photo(high_res_frame):
                            """Handle high-resolution photo capture."""
                            try:
                                from photo import capture
                                from visitations import add_padding_to_bbox
                                
                                height_hr, width_hr = high_res_frame.shape[:2]
                                height_det, width_det = current_frame.shape[:2]
                                
                                if visitations.visitation_id:
                                    # Save high-res full photo
                                    max_score = max([obj.score for obj in current_objs]) * 100 if current_objs else 0
                                    capture(
                                        high_res_frame,
                                        visitations.visitation_id,
                                        int(max_score),
                                        'full_12mp'
                                    )
                                    logger.info(f"Captured 12MP full photo for visitation {visitations.visitation_id}")
                                    
                                    # Save high-res boxed photos for each bird detection
                                    for obj in current_objs:
                                        if labels.get(obj.id, "").lower() == 'bird' and obj.score >= 0.4:
                                            # Scale bbox from detection frame (normalized) to high-res coordinates
                                            x0 = int(obj.bbox.xmin * width_hr)
                                            y0 = int(obj.bbox.ymin * height_hr)
                                            x1 = int(obj.bbox.xmax * width_hr)
                                            y1 = int(obj.bbox.ymax * height_hr)
                                            
                                            # Add padding
                                            padded_x0, padded_y0, padded_x1, padded_y1 = add_padding_to_bbox(
                                                [x0, y0, x1, y1],
                                                width_hr,
                                                height_hr,
                                                50
                                            )
                                            
                                            # Crop and save
                                            boxed_hr = high_res_frame[
                                                padded_y0:padded_y1,
                                                padded_x0:padded_x1
                                            ]
                                            
                                            capture(
                                                boxed_hr,
                                                visitations.visitation_id,
                                                int(obj.score * 100),
                                                'boxed_12mp'
                                            )
                                            logger.info(f"Captured 12MP boxed photo for visitation {visitations.visitation_id}")
                                            
                            except Exception as e:
                                logger.exception(f"Error handling high-res photo: {e}")
                        
                        camera.capture_high_res_photo(handle_high_res_photo)
                        last_photo_time = current_time

                # Log periodically
                if frame_count % 30 == 0:
                    logger.debug(
                        f"Processed {frame_count} frames, "
                        f"{len(objs)} detections, "
                        f"bird_detected={bird_detected}"
                    )

                # Check for quit key (if display window is open)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("Quit key pressed")
                    break

            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
            except Exception as e:
                logger.exception(f"Error in detection loop: {e}")
                # Continue processing despite errors
                time.sleep(0.1)

        logger.info("Shutting down...")

    except Exception as e:
        logger.exception("Fatal error in main program")
        sys.exit(1)
    finally:
        # Guaranteed cleanup
        if camera is not None:
            camera.release()
        cv2.destroyAllWindows()
        if hailo is not None:
            hailo.cleanup()
        logger.info("Shutdown complete")


if __name__ == '__main__':
    main()
