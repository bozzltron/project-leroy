#!/usr/bin/env python3
"""
Project Leroy - Bird Classification System
Raspberry Pi 5 + AI Kit (Hailo) Implementation
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

from setup_logging import setup_logging
setup_logging()
logger = logging.getLogger(__name__)


def get_new_dir(dirpath):
    """Get new directory path for classified images."""
    new_dir = ""
    path_sections = dirpath.split("/")
    if len(path_sections) == 4:
        date = path_sections[2]
        visitation_id = path_sections[3]
        new_dir = "/var/www/html/classified/{}/{}".format(date, visitation_id)
    return new_dir


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


def main():
    """Main classification function."""
    parser = argparse.ArgumentParser(
        description='Project Leroy - Bird Classification with Hailo AI Kit'
    )
    parser.add_argument(
        '--classification-model',
        default='all_models/mobilenet_v3.hef',
        help='Classification HEF model path'
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
                        results = hailo.classify(img, top_k=args.top_k, threshold=args.threshold)

                        if results:
                            class_id, score = results[0]
                            label = labels.get(class_id, "unknown")

                            # Update metadata with classification
                            if "classifications" not in metadata:
                                metadata["classifications"] = []

                            scientific_name, common_name = split_scientific_common(label)
                            metadata["classifications"].append({
                                "species": common_name.replace(" ", "-"),
                                "scientific_name": scientific_name,
                                "score": float(score),
                                "confidence": "high" if score >= 0.8 else "medium" if score >= 0.5 else "low"
                            })

                            new_dir = get_new_dir(dirpath)

                            # Move image and metadata
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

    hailo.cleanup()
    logger.info("Classification finished")


if __name__ == '__main__':
    main()
