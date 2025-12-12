#!/usr/bin/env python3
"""
Project Leroy - Bird Classification System
Raspberry Pi 5 + AI Kit (Hailo) Implementation
"""
import argparse
import os
import shutil
import logging
from PIL import Image
from hailo_inference import HailoInference
from active_learning import ActiveLearningCollector
from utils import load_labels

# Initialize logging
logging.basicConfig(
    filename='storage/results.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
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


def main():
    """Main classification function."""
    parser = argparse.ArgumentParser(
        description='Project Leroy - Bird Classification with Hailo AI Kit'
    )
    # Try to find classification model - check for various MobileNet versions
    default_model_dir = os.path.join('all_models')
    mobilenet_v3_path = os.path.join(default_model_dir, 'mobilenet_v3.hef')
    mobilenet_v2_path = os.path.join(default_model_dir, 'mobilenet_v2_1.0_224_inat_bird.hef')
    mobilenet_v2_alt_path = os.path.join(default_model_dir, 'mobilenet_v2.hef')
    
    if os.path.exists(mobilenet_v3_path):
        default_classification_model = mobilenet_v3_path
    elif os.path.exists(mobilenet_v2_path):
        default_classification_model = mobilenet_v2_path
    elif os.path.exists(mobilenet_v2_alt_path):
        default_classification_model = mobilenet_v2_alt_path
    else:
        default_classification_model = mobilenet_v2_path  # Default (will error clearly if missing)
    
    parser.add_argument(
        '--model',
        help='HEF model path',
        default=default_classification_model
    )
    parser.add_argument(
        '--label',
        help='Label file path',
        default=os.path.join('all_models', 'inat_bird_labels.txt')
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

    logger.info(f"Starting classification")
    logger.info(f"Model: {args.model}, Labels: {args.label}")

    # Initialize Hailo inference
    logger.info("Initializing Hailo AI Kit...")
    hailo = HailoInference()
    hailo.initialize()
    hailo.load_classification_model(args.model)

    # Load labels
    labels = load_labels(args.label)
    logger.info(f"Loaded {len(labels)} labels")
    
    # Initialize active learning collector
    active_learning = ActiveLearningCollector()

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

        # Track processed files to avoid duplicates
        processed_boxed = set()
        processed_full = set()
        
        for dirpath, dirnames, filenames in os.walk(args.dir):
            for filename in filenames:
                try:
                    filepath = os.path.join(dirpath, filename)

                    if "boxed" in filename and filename.endswith('.png'):
                        # Skip JSON metadata files
                        if filename.endswith('.json'):
                            continue
                        
                        # Check if this is a UUID-based filename (new format)
                        # UUID format: {uuid}.png or {uuid}_full.png
                        is_uuid_format = len(filename.replace('.png', '').replace('_full', '').split('-')) == 5
                        
                        if is_uuid_format:
                            # New format: Load metadata, update with classification, save both
                            from photo_metadata import PhotoMetadata
                            
                            metadata = PhotoMetadata.find_metadata_for_image(filepath)
                            if not metadata:
                                logger.warning(f"No metadata found for {filepath}, skipping")
                                continue
                            
                            logger.info(f"Classifying {filepath} (UUID format)")
                            img = Image.open(filepath)
                            results = hailo.classify(img, top_k=args.top_k, threshold=args.threshold)
                            
                            if results:
                                class_id, score = results[0]
                                label = labels.get(class_id, "unknown")
                                
                                # Update metadata with classification
                                if "classifications" not in metadata:
                                    metadata["classifications"] = []
                                
                                metadata["classifications"].append({
                                    "species": label.replace(" ", "-"),
                                    "scientific_name": "Unknown",  # TODO: Extract from labels
                                    "score": float(score),
                                    "confidence": "high" if score >= 0.8 else "medium" if score >= 0.5 else "low"
                                })
                                
                                # Determine new directory
                                path_sections = dirpath.split("/")
                                new_dir = "/var/www/html/classified/"
                                if len(path_sections) == 4:
                                    date = path_sections[2]
                                    visitation_id = path_sections[3]
                                    new_dir = "/var/www/html/classified/{}/{}".format(date, visitation_id)
                                
                                # Move image and metadata
                                new_image_path = os.path.join(new_dir, filename)
                                metadata_path = PhotoMetadata.get_metadata_filename(metadata["photo_id"], metadata["photo_type"])
                                new_metadata_path = os.path.join(new_dir, metadata_path)
                                
                                if not args.dryrun:
                                    os.makedirs(new_dir, exist_ok=True)
                                    shutil.move(os.path.abspath(filepath), os.path.abspath(new_image_path))
                                    PhotoMetadata.save_metadata(metadata, new_metadata_path)
                                    logger.info(f"Moved {filepath} -> {new_image_path} (with metadata)")
                                else:
                                    logger.info(f"[DRYRUN] Would move {filepath} -> {new_image_path}")
                                
                                processed_count += 1
                            continue
                        
                        # Old format: Legacy filename parsing
                        # Skip if we've already processed a higher-res version
                        base_name = filename.replace("_12mp", "").replace("boxed", "").replace(".png", "")
                        if base_name in processed_boxed and "_12mp" not in filename:
                            logger.debug(f"Skipping {filename} (higher-res version already processed)")
                            continue
                        
                        processed_boxed.add(base_name)
                        logger.info(f"Classifying {filepath}")
                        img = Image.open(filepath)
                        results = hailo.classify(img, top_k=args.top_k, threshold=args.threshold)

                        if results:
                            # Get top result
                            class_id, score = results[0]
                            label = labels.get(class_id, "unknown")
                            percent = int(100 * score)
                            
                            # Collect for active learning if confidence is low
                            if score < 0.5:  # Low confidence - unknown bird
                                active_learning.collect_unknown_bird(
                                    img, 1.0, results, labels, 
                                    os.path.basename(os.path.dirname(filepath))
                                )
                            elif 0.5 <= score < 0.8:  # Medium confidence - worth reviewing
                                active_learning.collect_low_confidence(
                                    img, 1.0, results, labels,
                                    os.path.basename(os.path.dirname(filepath))
                                )

                            if label != "background":
                                # Determine new directory
                                path_sections = dirpath.split("/")
                                new_dir = "/var/www/html/classified/"
                                if len(path_sections) == 4:
                                    date = path_sections[2]
                                    visitation_id = path_sections[3]
                                    new_dir = "/var/www/html/classified/{}/{}".format(date, visitation_id)

                                # Create new filename with species and score
                                newname = filename.replace(
                                    ".png",
                                    "_{}_{}.png".format(label.replace(" ", "-"), percent)
                                )
                                newpath = os.path.join(new_dir, newname)

                                logger.info(f"Moving {filepath} -> {newpath}")

                                if not args.dryrun:
                                    os.makedirs(new_dir, exist_ok=True)
                                    shutil.move(os.path.abspath(filepath), os.path.abspath(newpath))
                                else:
                                    logger.info(f"[DRYRUN] Would move {filepath} -> {newpath}")

                                processed_count += 1

                    elif "full" in filename and filename.endswith('.png'):
                        # Skip JSON metadata files
                        if filename.endswith('.json'):
                            continue
                        
                        # Check if this is a UUID-based filename (new format)
                        is_uuid_format = len(filename.replace('.png', '').replace('_full', '').split('-')) == 5
                        
                        if is_uuid_format:
                            # New format: Just move image and metadata
                            from photo_metadata import PhotoMetadata
                            
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
                                        PhotoMetadata.save_metadata(metadata, new_metadata_path)
                                        logger.info(f"Moved {filepath} -> {new_image_path} (with metadata)")
                                    else:
                                        logger.info(f"[DRYRUN] Would move {filepath} -> {new_image_path}")
                            continue
                        
                        # Old format: Legacy handling
                        base_name = filename.replace("_12mp", "").replace("full", "").replace(".png", "")
                        if base_name in processed_full and "_12mp" not in filename:
                            logger.debug(f"Skipping {filename} (higher-res version already processed)")
                            continue
                        
                        processed_full.add(base_name)
                        
                        new_dir = get_new_dir(dirpath)
                        if new_dir:
                            new_path = os.path.join(new_dir, filename)
                            logger.info(f"Moving full image {filepath} -> {new_path}")

                            if not args.dryrun:
                                if os.path.exists(new_dir):
                                    shutil.move(os.path.abspath(filepath), os.path.abspath(new_path))
                                else:
                                    logger.warning(f"Target directory does not exist: {new_dir}")
                            else:
                                logger.info(f"[DRYRUN] Would move {filepath} -> {new_path}")

                except Exception as e:
                    error_count += 1
                    logger.error(f"Failed to classify {filepath}: {e}")

        logger.info(f"Classification complete: {processed_count} processed, {error_count} errors")

    hailo.cleanup()
    logger.info("Classification finished")


if __name__ == '__main__':
    main()
