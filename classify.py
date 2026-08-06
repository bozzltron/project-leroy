#!/usr/bin/env python3
"""
Project Leroy - Bird Classification System
Raspberry Pi 5 + AI Kit (Hailo-8L) Implementation

Supports both Hailo HEF models (accelerated via Hailo-8L NPU) and ONNX
models (CPU fallback). HEF models compiled for Hailo-8 (26 TOPS) are
incompatible with the Hailo-8L (13 TOPS) used in the Pi AI Kit.
"""
import argparse
import os
import re
import shutil
import logging
from pathlib import Path
from PIL import Image
from hailo_inference import HailoInference
from photo_metadata import PhotoMetadata
from utils import load_labels

try:
    import onnxruntime as ort
    import numpy as np
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False

from setup_logging import setup_logging
setup_logging()
logger = logging.getLogger(__name__)


def get_new_dir(dirpath):
    """Get classified directory path for images.

    Works with both source paths (storage/detected/{date}/{visitation_id})
    and already-classified paths (/var/www/html/classified/{date}/{visitation_id}).
    """
    path_sections = dirpath.split("/")
    # Look for date + visitation_id pattern in the path
    date = None
    visitation_id = None
    for i, section in enumerate(path_sections):
        if re.match(r'^\d{4}-\d{2}-\d{2}$', section):
            date = section
            if i + 1 < len(path_sections):
                visitation_id = path_sections[i + 1]
            break
    if date and visitation_id:
        return "/var/www/html/classified/{}/{}".format(date, visitation_id)
    return ""


def move_metadata(filepath, new_metadata_path, metadata):
    """Move the source metadata JSON alongside the photo, leaving no copy behind.

    Falls back to writing a copy if the source JSON is missing.
    """
    src_metadata = str(Path(filepath).with_suffix('.json'))
    if os.path.exists(src_metadata):
        shutil.move(os.path.abspath(src_metadata), os.path.abspath(new_metadata_path))
    else:
        PhotoMetadata.save_metadata(metadata, new_metadata_path)


def split_scientific_common(label):
    """Split an iNaturalist-style label 'Scientific (Common)' into its parts.

    Labels without the '(Common)' suffix (e.g. plain ImageNet names or
    'background') pass through unchanged with scientific_name 'Unknown'.
    """
    m = re.match(r'^\s*(.+?)\s+\((.+)\)\s*$', label)
    if m:
        return m.group(1), m.group(2)
    return "Unknown", label


def classify_with_onnx(image, model_path, labels, top_k=3, threshold=0.1):
    """Run classification using ONNX Runtime (CPU fallback).

    Uses preprocessing parameters from the companion JSON model config file
    (e.g. species_classifier_nabirds.json for rgb_mean/rgb_std).

    Args:
        image: PIL Image to process
        model_path: Path to ONNX model file
        labels: Loaded labels dict
        top_k: Number of top classifications to return
        threshold: Minimum confidence score (after softmax)

    Returns:
        List of (class_id, score) tuples
    """
    if not ONNXRUNTIME_AVAILABLE:
        raise RuntimeError("ONNX Runtime not available. Install: pip install onnxruntime")

    # Load config JSON for normalization parameters (same base name as ONNX)
    json_path = os.path.splitext(model_path)[0] + ".json"
    rgb_mean = [0.485, 0.456, 0.406]  # Default ImageNet mean
    rgb_std = [0.229, 0.224, 0.225]   # Default ImageNet std
    if os.path.exists(json_path):
        import json as json_mod
        with open(json_path) as f:
            cfg = json_mod.load(f)
        if 'rgb_mean' in cfg:
            rgb_mean = cfg['rgb_mean']
        if 'rgb_std' in cfg:
            rgb_std = cfg['rgb_std']

    # Load ONNX model
    sess = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
    input_name = sess.get_inputs()[0].name

    # Determine input size from model
    input_shape = sess.get_inputs()[0].shape
    if len(input_shape) == 4:
        _, _, height, width = input_shape
    else:
        height, width = 256, 256

    # Preprocess: resize, normalize, transpose to NCHW
    resized = image.resize((width, height), Image.LANCZOS)
    img_array = np.array(resized, dtype=np.float32) / 255.0  # HWC, 0-1
    # Normalize per channel
    img_array[:, :, 0] = (img_array[:, :, 0] - rgb_mean[0]) / rgb_std[0]
    img_array[:, :, 1] = (img_array[:, :, 1] - rgb_mean[1]) / rgb_std[1]
    img_array[:, :, 2] = (img_array[:, :, 2] - rgb_mean[2]) / rgb_std[2]
    # Transpose HWC -> CHW and add batch dimension
    input_array = np.transpose(img_array, (2, 0, 1))[np.newaxis, ...]
    input_array = np.ascontiguousarray(input_array, dtype=np.float32)

    # Run inference
    results = sess.run(None, {input_name: input_array})
    output = results[0].flatten()

    # Apply softmax if output looks like logits
    if output.min() < 0 or output.max() > 1.0:
        exp = np.exp(output - np.max(output))
        output = exp / np.sum(exp)

    # Get top_k results
    top_indices = np.argsort(output)[::-1][:top_k]
    classifications = []
    for idx in top_indices:
        score = float(output[idx])
        if score >= threshold:
            classifications.append((int(idx), score))

    return classifications


def main():
    """Main classification function."""
    parser = argparse.ArgumentParser(
        description='Project Leroy - Bird Classification with Hailo AI Kit'
    )
    parser.add_argument(
        '--classification-model',
        default='all_models/mobilenet_v3.hef',
        help='Classification model path (.hef for Hailo or .onnx for ONNX Runtime)'
    )
    parser.add_argument(
        '--classification-labels',
        default='all_models/mobilenet_v3.txt',
        help='Classification label file path'
    )
    parser.add_argument(
        '--image',
        help='File path of the image to be recognized',
        required=False
    )
    parser.add_argument(
        '--dir',
        help='File path of the dir to be recognized',
        required=False
    )
    parser.add_argument(
        '--dryrun',
        help='Whether to actually move files or not',
        action='store_true',
        default=False
    )
    parser.add_argument(
        '--top_k',
        type=int,
        default=3,
        help='Number of classes with highest score to display'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.1,
        help='Class score threshold'
    )
    args = parser.parse_args()

    # Resolve relative paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(args.classification_model):
        args.classification_model = os.path.join(script_dir, args.classification_model)
    if not os.path.isabs(args.classification_labels):
        args.classification_labels = os.path.join(script_dir, args.classification_labels)

    logger.info(f"Starting classification")
    logger.info(f"Model: {args.classification_model}, Labels: {args.classification_labels}")

    # Determine model type based on file extension
    is_onnx = args.classification_model.endswith('.onnx')
    
    if is_onnx:
        if not ONNXRUNTIME_AVAILABLE:
            raise RuntimeError("ONNX model specified but onnxruntime not installed")
        logger.info("Using ONNX Runtime (CPU) for classification")
    else:
        hailo = HailoInference()
        hailo.initialize()
        hailo.load_classification_model(args.classification_model)
    
    labels = load_labels(args.classification_labels)
    logger.info(f"Loaded {len(labels)} labels")
    
    # Process single image
    if args.image:
        try:
            img = Image.open(args.image)
            results = hailo.classify(img, top_k=args.top_k, threshold=args.threshold)
            
            print('---------------------------')
            for class_id, score in results:
                label = labels.get(class_id, f"Class {class_id}")
                print(f"{label}: {score:.4f}")
        except Exception as e:
            logger.error(f"Failed to classify image {args.image}: {e}")
            print(f"Error: {e}")

    # Process directory
    if args.dir:
        if not os.path.isdir(args.dir):
            logger.error(f"Directory does not exist: {args.dir}")
            return

        processed_count = 0
        error_count = 0

        for dirpath, dirnames, filenames in os.walk(args.dir):
            for filename in filenames:
                try:
                    filepath = os.path.join(dirpath, filename)

                    if filename.endswith('.png') and '_full' not in filename:
                        # Skip JSON metadata files
                        if filename.endswith('.json'):
                            continue

                        # UUID format: {uuid}.png (boxed crop) or {uuid}_full.png (wide shot)
                        metadata = PhotoMetadata.find_metadata_for_image(filepath)
                        if not metadata:
                            logger.warning(f"No metadata found for {filepath}, skipping")
                            continue

                        logger.info(f"Classifying {filepath}")
                        img = Image.open(filepath)
                        
                        if is_onnx:
                            results = classify_with_onnx(img, args.classification_model, labels, top_k=args.top_k, threshold=args.threshold)
                        else:
                            results = hailo.classify(img, top_k=args.top_k, threshold=args.threshold)

                        if results:
                            class_id, score = results[0]
                            label = labels.get(class_id, "unknown")

                            # Update metadata with classification
                            # Reset the list so reclassification does not accumulate duplicates.
                            metadata["classifications"] = []

                            scientific_name, common_name = split_scientific_common(label)
                            metadata["classifications"].append({
                                "species": common_name.replace(" ", "-"),
                                "scientific_name": scientific_name,
                                "score": float(score),
                                "confidence": "high" if score >= 0.8 else "medium" if score >= 0.5 else "low"
                            })

                            new_dir = get_new_dir(dirpath)

                            # If already in classified dir, update metadata in place
                            # (supports reclassification with a new model)
                            if new_dir == os.path.abspath(dirpath):
                                logger.info(f"Re-classifying in place: {filepath}")
                                meta_path = os.path.join(dirpath, PhotoMetadata.get_metadata_filename(
                                    metadata["photo_id"], metadata["photo_type"]))
                                PhotoMetadata.save_metadata(metadata, meta_path)
                            elif new_dir:
                                # Move image and metadata to classified dir
                                new_image_path = os.path.join(new_dir, filename)
                                metadata_path = PhotoMetadata.get_metadata_filename(metadata["photo_id"], metadata["photo_type"])
                                new_metadata_path = os.path.join(new_dir, metadata_path)

                                if not args.dryrun:
                                    os.makedirs(new_dir, exist_ok=True)
                                    shutil.move(os.path.abspath(filepath), os.path.abspath(new_image_path))
                                    move_metadata(filepath, new_metadata_path, metadata)
                                    logger.info(f"Moved {filepath} -> {new_image_path} (with metadata)")
                                else:
                                    logger.info(f"[DRYRUN] Would move {filepath} -> {new_image_path}")
                            else:
                                # Already in classified dir (new_dir == "" but path has classified in it)
                                meta_filename = PhotoMetadata.get_metadata_filename(metadata["photo_id"], metadata["photo_type"])
                                meta_path = os.path.join(dirpath, meta_filename)
                                logger.info(f"Updating metadata in place: {meta_path}")
                                if not args.dryrun:
                                    PhotoMetadata.save_metadata(metadata, meta_path)
                            processed_count += 1

                    elif filename.endswith('_full.png'):
                        # Skip JSON metadata files
                        if filename.endswith('.json'):
                            continue

                        # UUID format: {uuid}.png (boxed crop) or {uuid}_full.png (wide shot)
                        metadata = PhotoMetadata.find_metadata_for_image(filepath)
                        if metadata:
                            new_dir = get_new_dir(dirpath)
                            if new_dir:
                                new_image_path = os.path.join(new_dir, filename)
                                metadata_path = PhotoMetadata.get_metadata_filename(metadata["photo_id"], "full")
                                new_metadata_path = os.path.join(new_dir, metadata_path)

                                if not args.dryrun:
                                    os.makedirs(new_dir, exist_ok=True)
                                    shutil.move(os.path.abspath(filepath), os.path.abspath(new_image_path))
                                    move_metadata(filepath, new_metadata_path, metadata)
                                    logger.info(f"Moved {filepath} -> {new_image_path} (with metadata)")
                                else:
                                    logger.info(f"[DRYRUN] Would move {filepath} -> {new_image_path}")
                            continue

                except Exception as e:
                    error_count += 1
                    logger.error(f"Failed to classify {filepath}: {e}")

        logger.info(f"Classification complete: {processed_count} processed, {error_count} errors")

    if not is_onnx:
        hailo.cleanup()
    logger.info("Classification finished")


if __name__ == '__main__':
    main()
