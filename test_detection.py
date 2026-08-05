#!/usr/bin/env python3
"""Standalone single-image detection test for Project Leroy.

Runs the YOLO detection HEF on one image (from file or live camera) and
prints every detection with its label, score, and bounding box. Uses a low
default threshold so weak detections are visible -- the live service in
leroy.py silently drops detections below 0.4 before logging or photographing.

The Hailo device is exclusive to one process, so leroy.service must be
stopped before running this. Example:

    venv/bin/python3 test_detection.py --image bird.jpg
    venv/bin/python3 test_detection.py --capture --out annotated.jpg --debug-raw

Exit codes: 0 = test ran (detections or not), 1 = setup/inference failure.
"""
import argparse
import logging
import os
import sys

import cv2
import numpy as np

from hailo_inference import HailoInference
from utils import load_labels

logger = logging.getLogger(__name__)


def dump_raw_output(hailo, pil_image, labels):
    """Print raw HEF output tensor names/shapes and which classes fired."""
    from hailo_platform import InferVStreams, InputVStreamParams, OutputVStreamParams

    network = hailo.detection_network
    input_data = hailo._preprocess_image(pil_image, network)
    in_params = InputVStreamParams.make(network)
    out_params = OutputVStreamParams.make(network)

    print("\nRaw output inspection:")
    with InferVStreams(network, in_params, out_params) as pipeline:
        results = pipeline.infer(input_data)

    for name, value in results.items():
        if isinstance(value, list):
            non_empty = []
            for i, arr in enumerate(value):
                if isinstance(arr, np.ndarray):
                    if arr.size:
                        non_empty.append(i)
                elif isinstance(arr, list) and arr:
                    non_empty.append(i)
            print(f"  output '{name}': list of {len(value)} per-class arrays")
            print(f"    non-empty class indices: {non_empty}")
            for i in non_empty:
                arr = value[i]
                if isinstance(arr, list):
                    arr = np.asarray(arr, dtype=object) if arr else np.array([])
                label = labels.get(i, f"class_{i}")
                print(f"    class {i} ({label}): shape={arr.shape}")
        else:
            arr = np.asarray(value)
            print(f"  output '{name}': ndarray shape={arr.shape} dtype={arr.dtype}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run YOLO detection on a single image or live camera frame."
    )
    parser.add_argument("--image", help="Path to input image (JPEG/PNG).")
    parser.add_argument("--capture", action="store_true",
                        help="Capture a frame from the camera instead of --image.")
    parser.add_argument("--model", default="all_models/yolov11s.hef")
    parser.add_argument("--labels", default="all_models/yolo11s.txt")
    parser.add_argument("--threshold", type=float, default=0.05,
                        help="Minimum confidence score (default 0.05).")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--out", help="Optional path to save annotated image.")
    parser.add_argument("--debug-raw", action="store_true",
                        help="Also dump raw HEF output shapes and classes.")
    args = parser.parse_args()

    if not args.image and not args.capture:
        parser.error("Provide --image <path> or use --capture.")

    labels = load_labels(args.labels)
    print(f"Loaded {len(labels)} labels from {args.labels}")

    if args.capture:
        print("Capturing frame from camera...")
        from camera_manager import CameraManager
        camera = CameraManager(camera_idx=0)
        if not camera.initialize():
            print("ERROR: failed to initialize camera")
            sys.exit(1)
        ret, frame = camera.get_detection_frame()
        camera.release()
        if not ret or frame is None:
            print("ERROR: failed to capture detection frame")
            sys.exit(1)
        print(f"Captured frame: {frame.shape[1]}x{frame.shape[0]}")
    else:
        if not os.path.exists(args.image):
            print(f"ERROR: image not found: {args.image}")
            sys.exit(1)
        frame = cv2.imread(args.image)
        if frame is None:
            print(f"ERROR: could not read image: {args.image}")
            sys.exit(1)
        print(f"Loaded image: {args.image} ({frame.shape[1]}x{frame.shape[0]})")

    from PIL import Image
    pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    hailo = HailoInference()
    try:
        hailo.initialize()
        hailo.load_detection_model(args.model)

        print(f"Running detection: model={args.model}, "
              f"threshold={args.threshold}, top_k={args.top_k}")
        detections = hailo.detect(pil_image,
                                  score_threshold=args.threshold,
                                  top_k=args.top_k)
    finally:
        pil_image.close()

    if args.debug_raw:
        dump_raw_output(hailo, Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), labels)

    if not detections:
        print("\nNO DETECTIONS at threshold " + str(args.threshold))
    else:
        print(f"\n{len(detections)} detection(s):")
        for det in detections:
            label = labels.get(det["id"], f"class_{det['id']}")
            b = det["bbox"]
            print(f"  class {det['id']:>3d}  {label:<20s} score={det['score']:.3f}  "
                  f"box=[x:{b['xmin']:.3f}-{b['xmax']:.3f} y:{b['ymin']:.3f}-{b['ymax']:.3f}]")

    if args.out:
        h, w = frame.shape[:2]
        for det in detections:
            label = labels.get(det["id"], str(det["id"]))
            b = det["bbox"]
            x0, y0 = int(b["xmin"] * w), int(b["ymin"] * h)
            x1, y1 = int(b["xmax"] * w), int(b["ymax"] * h)
            cv2.rectangle(frame, (x0, y0), (x1, y1), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} {det['score']:.2f}", (x0, max(0, y0 - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.imwrite(args.out, frame)
        print(f"Annotated image saved to {args.out}")

    hailo.cleanup()


if __name__ == "__main__":
    main()
