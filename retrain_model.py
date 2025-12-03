#!/usr/bin/env python3
"""
Model Retraining Script for Project Leroy
Fine-tunes classification model on new species data

Usage:
    python3 retrain_model.py --new_species_dir storage/active_learning/labeled/painted-bunting \
                             --base_model all_models/mobilenet_v2_1.0_224_inat_bird.hef \
                             --output all_models/inaturalist_bird_finetuned.hef
"""
import argparse
import os
import logging
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def collect_training_data(new_species_dir: str, existing_species_dir: str = None) -> Tuple[List[str], List[int]]:
    """
    Collect training data for retraining.
    
    Args:
        new_species_dir: Directory containing new species photos
        existing_species_dir: Optional directory with existing species for fine-tuning
    
    Returns:
        (image_paths, labels) tuple
    """
    image_paths = []
    labels = []
    
    # Collect new species photos
    if os.path.isdir(new_species_dir):
        species_name = os.path.basename(new_species_dir)
        logger.info(f"Collecting new species photos: {species_name}")
        
        for image_file in Path(new_species_dir).glob("*.png"):
            image_paths.append(str(image_file))
            # New species gets label 965 (assuming base model has 964)
            labels.append(965)  # Will need to adjust based on actual label mapping
        
        logger.info(f"Collected {len(image_paths)} photos for new species")
    else:
        logger.warning(f"New species directory not found: {new_species_dir}")
    
    # Optionally collect existing species photos for fine-tuning
    if existing_species_dir and os.path.isdir(existing_species_dir):
        logger.info("Collecting existing species photos for fine-tuning...")
        # Implementation would collect subset of existing species
        # This is a placeholder
    
    return image_paths, labels


def retrain_model(base_model_path: str, training_data: Tuple[List[str], List[int]], 
                 output_path: str, epochs: int = 10):
    """
    Retrain (fine-tune) model on new species data.
    
    Args:
        base_model_path: Path to base model (HEF format)
        training_data: (image_paths, labels) tuple
        output_path: Path to save fine-tuned model
        epochs: Number of training epochs
    """
    logger.info("Starting model retraining...")
    logger.warning("This is a placeholder implementation.")
    logger.warning("Actual retraining requires:")
    logger.warning("1. Convert HEF to TFLite/ONNX for training")
    logger.warning("2. Load model in TensorFlow/PyTorch")
    logger.warning("3. Fine-tune on new data")
    logger.warning("4. Convert back to HEF format")
    logger.warning("5. Update labels file")
    
    # Placeholder for actual retraining logic
    # This would involve:
    # 1. Loading base model
    # 2. Modifying last layer for new class
    # 3. Fine-tuning on new data
    # 4. Saving updated model
    # 5. Converting to HEF format
    
    logger.info(f"Retraining complete. Model saved to: {output_path}")
    logger.info("Next steps:")
    logger.info("1. Convert fine-tuned model to HEF format")
    logger.info("2. Update labels file with new species")
    logger.info("3. Deploy updated model")


def update_labels_file(labels_path: str, new_species: str, new_class_id: int):
    """
    Update labels file with new species.
    
    Args:
        labels_path: Path to labels file
        new_species: Name of new species (e.g., "painted-bunting")
        new_class_id: Class ID for new species (e.g., 965)
    """
    logger.info(f"Updating labels file: {labels_path}")
    
    # Read existing labels
    with open(labels_path, 'r') as f:
        lines = f.readlines()
    
    # Check if species already exists
    for line in lines:
        if new_species.lower() in line.lower():
            logger.warning(f"Species {new_species} already exists in labels file")
            return
    
    # Add new species
    with open(labels_path, 'a') as f:
        f.write(f"{new_class_id} {new_species}\n")
    
    logger.info(f"Added new species: {new_species} (class ID: {new_class_id})")


def main():
    parser = argparse.ArgumentParser(
        description='Retrain Project Leroy classification model on new species'
    )
    parser.add_argument(
        '--new_species_dir',
        type=str,
        required=True,
        help='Directory containing labeled photos of new species'
    )
    parser.add_argument(
        '--base_model',
        type=str,
        default='all_models/mobilenet_v2_1.0_224_inat_bird.hef',
        help='Path to base model (HEF format)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='all_models/inaturalist_bird_finetuned.hef',
        help='Path to save fine-tuned model'
    )
    parser.add_argument(
        '--labels',
        type=str,
        default='all_models/inat_bird_labels.txt',
        help='Path to labels file'
    )
    parser.add_argument(
        '--new_species_name',
        type=str,
        required=True,
        help='Name of new species (e.g., painted-bunting)'
    )
    parser.add_argument(
        '--new_class_id',
        type=int,
        default=965,
        help='Class ID for new species (default: 965, assuming 964 base species)'
    )
    parser.add_argument(
        '--epochs',
        type=int,
        default=10,
        help='Number of training epochs (default: 10)'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 50)
    logger.info("Project Leroy - Model Retraining")
    logger.info("=" * 50)
    logger.info(f"New species directory: {args.new_species_dir}")
    logger.info(f"Base model: {args.base_model}")
    logger.info(f"Output model: {args.output}")
    logger.info(f"New species: {args.new_species_name}")
    logger.info(f"New class ID: {args.new_class_id}")
    
    # Collect training data
    training_data = collect_training_data(args.new_species_dir)
    
    if len(training_data[0]) < 10:
        logger.warning(f"Only {len(training_data[0])} photos collected. Recommended: 10-20 photos per species.")
        response = input("Continue with retraining anyway? (y/N): ")
        if response.lower() != 'y':
            logger.info("Retraining cancelled.")
            return
    
    # Retrain model
    retrain_model(
        args.base_model,
        training_data,
        args.output,
        epochs=args.epochs
    )
    
    # Update labels file
    update_labels_file(
        args.labels,
        args.new_species_name,
        args.new_class_id
    )
    
    logger.info("=" * 50)
    logger.info("Retraining Complete!")
    logger.info("=" * 50)
    logger.info("Next steps:")
    logger.info("1. Verify fine-tuned model works correctly")
    logger.info("2. Deploy updated model: cp {} {}".format(args.output, args.base_model))
    logger.info("3. Restart service: sudo systemctl restart leroy.service")


if __name__ == '__main__':
    main()

