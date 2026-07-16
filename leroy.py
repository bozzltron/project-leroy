#!/usr/bin/env python3
"""
Project Leroy - Bird Detection System
Raspberry Pi 5 + AI Kit (Hailo) Implementation

Dual-Resolution Strategy:
- Detection: Configurable resolution for fast processing
- Photos: Configurable high-resolution for quality captures when bird detected
"""
import argparse
import collections
import cv2
import os
import sys
import logging
import imutils
import time
import signal
import subprocess
from PIL import Image
from visitations import Visitations
from hailo_inference import HailoInference
from camera_manager import CameraManager
from active_learning import ActiveLearningCollector
from utils import load_labels, NON_BIRD_CLASSES

print("OpenCV version: " + cv2.__version__)

Object = collections.namedtuple('Object', ['id', 'score', 'bbox'])

# Ensure storage directory exists before logging
os.makedirs('storage', exist_ok=True)

from setup_logging import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# Thermal protection
# Pi 5 throttles at 80°C (176°F) — pause just before throttle to maintain
# full performance. Resume at 75°C (167°F) for 5°C headroom.
THERMAL_PAUSE_C = 80.0  # Pause detection above this temperature
THERMAL_RESUME_C = 75.0  # Resume detection below this temperature
THERMAL_CHECK_INTERVAL = 10  # Check every N seconds


def get_cpu_temp_c():
    """Read CPU temperature from vcgencmd. Returns float in Celsius, or None on error."""
    try:
        result = subprocess.run(
            ['vcgencmd', 'measure_temp'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            # Output format: "temp=87.3'C"
            temp_str = result.stdout.strip().replace("temp=", "").replace("'C", "")
            return float(temp_str)
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


def celsius_to_fahrenheit(c):
    return c * 9 / 5 + 32


class BBox(collections.namedtuple('BBox', ['xmin', 'ymin', 'xmax', 'ymax'])):
    """Bounding box.
    Represents a rectangle which sides are either vertical or horizontal, parallel
    to the x or y axis.
    """
    __slots__ = ()


def filter_and_categorize_detections(objs, labels, threshold=0.4):
    """
    Filter detections into birds and non-birds (squirrels, cats, etc).
    
    Returns:
        (birds, non_birds) tuple of Object lists
    """
    birds = []
    non_birds = []
    non_bird_classes = NON_BIRD_CLASSES

    for obj in objs:
        label = labels.get(obj.id, "").lower()
        if obj.score < threshold:
            continue
        if label == 'bird':
            birds.append(obj)
        elif label in non_bird_classes:
            non_birds.append(obj)

    return birds, non_birds


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
        script_dir = os.path.dirname(os.path.abspath(__file__))

        parser = argparse.ArgumentParser(
            description='Project Leroy - Bird Detection with Hailo AI Kit'
        )
        parser.add_argument(
            '--detection-model',
            default='all_models/yolov11s.hef',
            help='Detection HEF model path'
        )
        parser.add_argument(
            '--detection-labels',
            default='all_models/yolo11s.txt',
            help='Detection label file path'
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

        # Resolve relative paths against project root
        if not os.path.isabs(args.detection_model):
            args.detection_model = os.path.join(script_dir, args.detection_model)
        if not os.path.isabs(args.detection_labels):
            args.detection_labels = os.path.join(script_dir, args.detection_labels)

        logger.info(f"Starting Project Leroy detection system")
        logger.info(f"Detection: {args.detection_model}, {args.detection_labels}")
        
        # Get resolution info from camera manager
        from config import get_config
        config = get_config()
        det_res = config['detection_resolution']
        photo_res = config['photo_resolution']
        logger.info(f"Dual-resolution strategy: {det_res[0]}x{det_res[1]} detection (resized to {args.detection_width}px), {photo_res[0]}x{photo_res[1]} photos")

        # Initialize Hailo inference
        logger.info("Initializing Hailo AI Kit...")
        hailo = HailoInference()
        hailo.initialize()
        hailo.load_detection_model(args.detection_model)
        
        # Load labels (HEF files don't contain labels)
        labels = load_labels(args.detection_labels)
        logger.info(f"Loaded {len(labels)} labels")

        # Initialize camera manager
        logger.info(f"Initializing camera (index {args.camera_idx})...")
        camera = CameraManager(camera_idx=args.camera_idx)
        if not camera.initialize():
            raise RuntimeError(f"Failed to initialize camera {args.camera_idx}")
        
        det_res = camera.get_detection_resolution()
        photo_res = camera.get_photo_resolution()
        logger.info(f"Camera initialized: Detection={det_res[0]}x{det_res[1]}, Photo={photo_res[0]}x{photo_res[1]}")

        # Initialize visitation tracking
        logger.info("Initializing visitation tracking...")
        visitations = Visitations()
        
        # Initialize active learning collector
        logger.info("Initializing active learning collector...")
        active_learning = ActiveLearningCollector()

        logger.info(f"Starting detection loop at {det_res[0]}x{det_res[1]} (resized to {args.detection_width}px for inference, {photo_res[0]}x{photo_res[1]} photos when bird detected)...")

        # Diagnostics: periodic summary
        SUMMARY_INTERVAL_SECONDS = 30

        logger.info(
            f"Detection loop starting: model={args.detection_model}, "
            f"threshold={args.threshold}, top_k={args.top_k}, "
            f"summary_interval={SUMMARY_INTERVAL_SECONDS}s"
        )

        # Log initial CPU temperature
        initial_temp = get_cpu_temp_c()
        if initial_temp is not None:
            logger.info(
                f"CPU temperature at startup: {initial_temp:.1f}°C "
                f"({celsius_to_fahrenheit(initial_temp):.1f}°F)"
            )
        frame_count = 0
        last_photo_time = 0
        photo_cooldown = 0.5  # Minimum seconds between high-res captures

        # Diagnostic and thermal state
        last_summary_time = time.time()
        last_thermal_check_time = time.time()
        thermal_paused = False
        window_frames = 0
        window_detections = []  # list of (label, score) tuples
        window_visitation_events = []  # list of strings like "started", "ended"

        while True:
            # Thermal protection: check CPU temp periodically, regardless of pause state
            if time.time() - last_thermal_check_time >= THERMAL_CHECK_INTERVAL:
                last_thermal_check_time = time.time()
                temp_c = get_cpu_temp_c()
                if temp_c is not None:
                    if temp_c >= THERMAL_PAUSE_C and not thermal_paused:
                        thermal_paused = True
                        logger.warning(
                            f"CPU temperature {temp_c:.1f}°C "
                            f"({celsius_to_fahrenheit(temp_c):.1f}°F) "
                            f"exceeds {THERMAL_PAUSE_C:.0f}°C — pausing "
                            f"detection until temp drops below "
                            f"{THERMAL_RESUME_C:.0f}°C "
                            f"({celsius_to_fahrenheit(THERMAL_RESUME_C):.0f}°F)"
                        )
                    elif temp_c < THERMAL_RESUME_C and thermal_paused:
                        thermal_paused = False
                        logger.info(
                            f"CPU temperature {temp_c:.1f}°C "
                            f"({celsius_to_fahrenheit(temp_c):.1f}°F) "
                            f"cooled below {THERMAL_RESUME_C:.0f}°C — resuming detection"
                        )

            # Thermal protection: if paused, sleep and skip detection
            if thermal_paused:
                time.sleep(5)
                continue

            try:
                # Get detection frame
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
                bird_objs, non_bird_objs = filter_and_categorize_detections(
                    objs, labels, threshold=0.4
                )
                
                # Track all detections for periodic summary
                for obj in objs:
                    label = labels.get(obj.id, "").lower()
                    if label and obj.score >= 0.4:
                        window_detections.append((label, obj.score))

                # Log non-bird detections (for learning) at DEBUG to avoid per-frame noise
                if non_bird_objs:
                    for obj in non_bird_objs:
                        label = labels.get(obj.id, "")
                        logger.debug(f"Non-bird detected: {label} (score: {obj.score:.2f})")
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
                prev_visitation_id = visitations.visitation_id
                visitations.update(bird_objs, frame, labels)
                if prev_visitation_id is None and visitations.visitation_id is not None:
                    window_visitation_events.append("started")
                elif prev_visitation_id is not None and visitations.visitation_id is None:
                    window_visitation_events.append("ended")

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
                                resolution = (width_hr, height_hr)
                                
                                if visitations.visitation_id:
                                    # Save high-res full photo
                                    max_score = max([obj.score for obj in current_objs]) if current_objs else 0
                                    capture(
                                        high_res_frame,
                                        visitations.visitation_id,
                                        max_score,  # Keep as float 0-1
                                        'full',
                                        resolution=resolution
                                    )
                                    logger.info(f"Captured full photo ({width_hr}x{height_hr}) for visitation {visitations.visitation_id}")
                                    
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
                                            
                                            bbox = (padded_x0, padded_y0, padded_x1, padded_y1)
                                            
                                            capture(
                                                boxed_hr,
                                                visitations.visitation_id,
                                                obj.score,  # Keep as float 0-1
                                                'boxed',
                                                resolution=resolution,
                                                detection_bbox=bbox
                                            )
                                            logger.info(f"Captured boxed photo ({width_hr}x{height_hr}) for visitation {visitations.visitation_id}")
                                            
                            except Exception as e:
                                logger.exception(f"Error handling photo capture: {e}")
                        
                        camera.capture_high_res_photo(handle_high_res_photo)
                        last_photo_time = current_time

                # Log periodically
                if frame_count % 30 == 0:
                    logger.debug(
                        f"Processed {frame_count} frames, "
                        f"{len(objs)} detections, "
                        f"bird_detected={bird_detected}"
                    )

                # Periodic summary at INFO level (bounded, scannable)
                window_frames += 1
                if time.time() - last_summary_time >= SUMMARY_INTERVAL_SECONDS:
                    elapsed = time.time() - last_summary_time
                    fps = window_frames / elapsed if elapsed > 0 else 0

                    if window_detections:
                        label_scores = {}
                        for label, score in window_detections:
                            if label not in label_scores or score > label_scores[label]:
                                label_scores[label] = score
                        top_labels = sorted(
                            label_scores.items(), key=lambda x: -x[1]
                        )[:5]
                        labels_str = ", ".join(
                            f"{label}@{score:.2f}" for label, score in top_labels
                        )
                        summary = (
                            f"{int(elapsed)}s summary: {window_frames} frames "
                            f"({fps:.1f} fps), {len(window_detections)} "
                            f"detections [{labels_str}]"
                        )
                        if window_visitation_events:
                            events_str = ", ".join(window_visitation_events)
                            summary += f", visitations: {events_str}"
                    else:
                        summary = (
                            f"{int(elapsed)}s summary: {window_frames} frames "
                            f"({fps:.1f} fps), 0 detections, no visitations"
                        )

                    logger.info(summary)

                    # Reset window (only here, not every frame)
                    last_summary_time = time.time()
                    window_frames = 0
                    window_detections = []
                    window_visitation_events = []

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
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
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
