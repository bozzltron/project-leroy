#!/bin/bash
# Simple Model Download - Uses git sparse-checkout to get only HEF files

set -e

echo "Downloading HEF models using git sparse-checkout..."

MODELS_DIR="all_models"
mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

# Temporary directory for cloning
TMP_DIR="/tmp/hailo_model_zoo_$$"
rm -rf "$TMP_DIR"

# Clone with sparse-checkout to get only HEF files
echo "Cloning Model Zoo (sparse checkout - only HEF files)..."
git clone --filter=blob:none --sparse --branch v2.15 --depth 1 \
    https://github.com/hailo-ai/hailo_model_zoo.git "$TMP_DIR"

cd "$TMP_DIR"

# Configure sparse-checkout to include HEF files
git sparse-checkout init --cone
git sparse-checkout set 'hailo_models/*/hef/*.hef'

# Find and copy HEF files
echo "Finding HEF files..."
find hailo_models -name "*.hef" -type f | while read hef_file; do
    model_name=$(basename "$hef_file" .hef)
    
    # Copy detection models
    if [[ "$model_name" == "yolov5s" ]]; then
        cp "$hef_file" "../../yolov5s.hef"
        size=$(stat -c%s "../../yolov5s.hef" 2>/dev/null || echo "unknown")
        echo "✓ Downloaded: yolov5s.hef ($size bytes)"
    elif [[ "$model_name" == "ssd_mobilenet_v2" ]]; then
        cp "$hef_file" "../../ssd_mobilenet_v2_coco.hef"
        size=$(stat -c%s "../../ssd_mobilenet_v2_coco.hef" 2>/dev/null || echo "unknown")
        echo "✓ Downloaded: ssd_mobilenet_v2_coco.hef ($size bytes)"
    elif [[ "$model_name" == "mobilenet_v2" ]]; then
        cp "$hef_file" "../../mobilenet_v2_1.0_224_inat_bird.hef"
        size=$(stat -c%s "../../mobilenet_v2_1.0_224_inat_bird.hef" 2>/dev/null || echo "unknown")
        echo "✓ Downloaded: mobilenet_v2_1.0_224_inat_bird.hef ($size bytes)"
    fi
done

# Cleanup
cd ../..
rm -rf "$TMP_DIR"

# Download label files
echo "Downloading label files..."
[ ! -f "coco_labels.txt" ] && \
    wget -q --show-progress "https://dl.google.com/coral/canned_models/coco_labels.txt" -O "coco_labels.txt" && \
    echo "✓ coco_labels.txt"

[ ! -f "inat_bird_labels.txt" ] && \
    wget -q --show-progress "https://github.com/google-coral/edgetpu/raw/master/test_data/inat_bird_labels.txt" -O "inat_bird_labels.txt" && \
    echo "✓ inat_bird_labels.txt"

echo ""
echo "Summary:"
[ -f "yolov5s.hef" ] && echo "  ✓ yolov5s.hef" || [ -f "ssd_mobilenet_v2_coco.hef" ] && echo "  ✓ ssd_mobilenet_v2_coco.hef" || echo "  ✗ No detection model"
[ -f "mobilenet_v2_1.0_224_inat_bird.hef" ] && echo "  ✓ mobilenet_v2_1.0_224_inat_bird.hef" || echo "  ⚠ No classification model (optional)"
[ -f "coco_labels.txt" ] && echo "  ✓ coco_labels.txt" || echo "  ✗ No COCO labels"
[ -f "inat_bird_labels.txt" ] && echo "  ✓ inat_bird_labels.txt" || echo "  ✗ No bird labels"
echo ""

