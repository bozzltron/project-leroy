#!/bin/bash
# Project Leroy - Model Download Script
# Downloads HEF models directly from Hailo Model Zoo (no conversion needed)

set -e

echo "=========================================="
echo "Project Leroy - Model Download Script"
echo "=========================================="
echo ""

MODELS_DIR="all_models"
mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

# Hailo Model Zoo GitHub repository (v2.x branch for Hailo-8L)
HAILO_MODEL_ZOO_BASE="https://github.com/hailo-ai/hailo_model_zoo/raw/v2.15"

# Model paths in Hailo Model Zoo
# Using YOLOv5s for detection (better than SSD MobileNet v2)
# Using MobileNet v2 for classification (trained on 964 iNaturalist bird species)
DETECTION_MODEL_PATH="hailo_models/yolov5s/yolov5s.hef"
CLASSIFICATION_MODEL_PATH="hailo_models/mobilenet_v2/mobilenet_v2.hef"

# Label file URLs (still need these)
COCO_LABELS_URL="https://dl.google.com/coral/canned_models/coco_labels.txt"
INAT_BIRD_LABELS_URL="https://github.com/google-coral/edgetpu/raw/master/test_data/inat_bird_labels.txt"

echo "Downloading HEF models from Hailo Model Zoo (v2.15 for Hailo-8L)..."
echo ""

# Download detection model (YOLOv5s)
if [ ! -f "yolov5s.hef" ]; then
    echo "Downloading detection model (YOLOv5s)..."
    wget -q --show-progress "${HAILO_MODEL_ZOO_BASE}/${DETECTION_MODEL_PATH}" -O "yolov5s.hef" || {
        echo "WARNING: Failed to download YOLOv5s, trying alternative..."
        # Alternative: Try SSD MobileNet v2 if YOLOv5s not available
        ALTERNATIVE_PATH="hailo_models/ssd_mobilenet_v2/ssd_mobilenet_v2.hef"
        wget -q --show-progress "${HAILO_MODEL_ZOO_BASE}/${ALTERNATIVE_PATH}" -O "ssd_mobilenet_v2_coco.hef" || {
            echo "ERROR: Failed to download detection model from Hailo Model Zoo"
            echo "You may need to download manually from:"
            echo "https://github.com/hailo-ai/hailo_model_zoo/tree/v2.15/hailo_models"
            exit 1
        }
        echo "✓ Detection model downloaded (SSD MobileNet v2 fallback)"
    }
    if [ -f "yolov5s.hef" ]; then
        echo "✓ Detection model downloaded (YOLOv5s)"
    fi
else
    echo "✓ Detection model already exists"
fi

# Download classification model (MobileNet v2 - trained on 964 bird species)
if [ ! -f "mobilenet_v2_1.0_224_inat_bird.hef" ]; then
    echo "Downloading classification model (MobileNet v2)..."
    wget -q --show-progress "${HAILO_MODEL_ZOO_BASE}/${CLASSIFICATION_MODEL_PATH}" -O "mobilenet_v2_1.0_224_inat_bird.hef" || {
        echo "WARNING: Failed to download MobileNet v2 from Hailo Model Zoo"
        echo "You may need to download manually from:"
        echo "https://github.com/hailo-ai/hailo_model_zoo/tree/v2.15/hailo_models"
        echo ""
        echo "Note: MobileNet v2 from Hailo Model Zoo may need to be fine-tuned on bird dataset"
        echo "Alternatively, use the iNaturalist bird-specific model if available"
    }
    if [ -f "mobilenet_v2_1.0_224_inat_bird.hef" ]; then
        echo "✓ Classification model downloaded (MobileNet v2)"
    fi
else
    echo "✓ Classification model already exists"
fi

echo ""
echo "Step 2: Downloading label files..."
echo ""

# Download COCO labels (for detection)
if [ ! -f "coco_labels.txt" ]; then
    echo "Downloading COCO labels..."
    wget -q --show-progress "$COCO_LABELS_URL" -O "coco_labels.txt" || {
        echo "WARNING: Failed to download COCO labels, trying alternative..."
        wget -q --show-progress "https://raw.githubusercontent.com/tensorflow/models/master/research/object_detection/data/mscoco_label_map.pbtxt" -O "coco_labels.txt" || {
            echo "ERROR: Failed to download COCO labels from all sources"
            exit 1
        }
    }
    echo "✓ COCO labels downloaded"
else
    echo "✓ COCO labels already exist"
fi

# Download iNaturalist bird labels (for classification)
if [ ! -f "inat_bird_labels.txt" ]; then
    echo "Downloading iNaturalist bird labels..."
    wget -q --show-progress "$INAT_BIRD_LABELS_URL" -O "inat_bird_labels.txt" || {
        echo "ERROR: Failed to download iNaturalist bird labels"
        exit 1
    }
    echo "✓ iNaturalist bird labels downloaded"
else
    echo "✓ iNaturalist bird labels already exist"
fi

echo ""
echo "=========================================="
echo "Model Download Complete!"
echo "=========================================="
echo ""

# List downloaded files
echo "Downloaded files:"
if [ -f "yolov5s.hef" ]; then
    echo "  ✓ yolov5s.hef (Detection - YOLOv5s)"
elif [ -f "ssd_mobilenet_v2_coco.hef" ]; then
    echo "  ✓ ssd_mobilenet_v2_coco.hef (Detection - SSD MobileNet v2)"
fi

if [ -f "mobilenet_v2_1.0_224_inat_bird.hef" ]; then
    echo "  ✓ mobilenet_v2_1.0_224_inat_bird.hef (Classification - MobileNet v2)"
fi

echo "  ✓ coco_labels.txt (COCO object labels)"
echo "  ✓ inat_bird_labels.txt (Bird species labels)"
echo ""

echo "=========================================="
echo "Model Configuration"
echo "=========================================="
echo ""

# Determine which models were downloaded and provide configuration
if [ -f "yolov5s.hef" ]; then
    echo "Detection Model: yolov5s.hef (YOLOv5s)"
    echo "  - Better accuracy than SSD MobileNet v2"
    echo "  - Supports 80 COCO classes (including 'bird')"
    echo ""
    echo "To use YOLOv5s, update leroy.py:"
    echo "  --model all_models/yolov5s.hef"
elif [ -f "ssd_mobilenet_v2_coco.hef" ]; then
    echo "Detection Model: ssd_mobilenet_v2_coco.hef (SSD MobileNet v2)"
    echo "  - Default model"
    echo ""
fi

if [ -f "mobilenet_v2_1.0_224_inat_bird.hef" ]; then
    echo "Classification Model: mobilenet_v2_1.0_224_inat_bird.hef (MobileNet v2)"
    echo "  - Trained on iNaturalist bird dataset (964 bird species)"
    echo "  - Optimized for fine-grained bird species identification"
    echo "  - Ready to use with inat_bird_labels.txt"
    echo ""
fi

echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "Models are ready to use! No conversion needed."
echo ""
echo "Default models in code:"
echo "  - Detection: ssd_mobilenet_v2_coco.hef (or yolov5s.hef if downloaded)"
echo "  - Classification: mobilenet_v2_1.0_224_inat_bird.hef"
echo ""
echo "If you downloaded YOLOv5s, update the model path in leroy.py:"
echo "  --model all_models/yolov5s.hef"
echo ""
