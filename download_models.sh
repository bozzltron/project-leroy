#!/bin/bash
# Project Leroy - Model Download Script
# Downloads pre-compiled HEF models (no compilation needed)

set +e

echo "Downloading pre-compiled HEF models..."

MODELS_DIR="all_models"
mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

# Hailo Model Zoo provides pre-compiled HEF files
# Try multiple repository paths and branches
HAILO_MODEL_ZOO_BASE="https://github.com/hailo-ai/hailo_model_zoo/raw"
HAILO_BRANCHES=("v2.15" "main" "master")

# Model paths - Hailo Model Zoo structure
# Pre-compiled HEF files are typically in: hailo_models/<model_name>/hef/<model_name>.hef
DETECTION_MODEL_PATHS=(
    "hailo_models/yolov5s/hef/yolov5s.hef"
    "hailo_models/yolov5s/yolov5s.hef"
    "models/yolov5s/hef/yolov5s.hef"
)

ALTERNATIVE_DETECTION_PATHS=(
    "hailo_models/ssd_mobilenet_v2/hef/ssd_mobilenet_v2.hef"
    "hailo_models/ssd_mobilenet_v2/ssd_mobilenet_v2.hef"
)

CLASSIFICATION_MODEL_PATHS=(
    "hailo_models/mobilenet_v2/hef/mobilenet_v2.hef"
    "hailo_models/mobilenet_v2/mobilenet_v2.hef"
)

# Label file URLs (still need these)
COCO_LABELS_URL="https://dl.google.com/coral/canned_models/coco_labels.txt"
INAT_BIRD_LABELS_URL="https://github.com/google-coral/edgetpu/raw/master/test_data/inat_bird_labels.txt"

# Download detection model (YOLOv5s)
DETECTION_DOWNLOADED=0
if [ ! -f "yolov5s.hef" ] && [ ! -f "ssd_mobilenet_v2_coco.hef" ]; then
    echo "Downloading detection model..."
    
    # Try each branch and path combination
    for branch in "${HAILO_BRANCHES[@]}"; do
        for path in "${DETECTION_MODEL_PATHS[@]}"; do
            url="${HAILO_MODEL_ZOO_BASE}/${branch}/${path}"
            if wget -q --show-progress "$url" -O "yolov5s.hef.tmp" 2>&1; then
                if [ -s "yolov5s.hef.tmp" ] && ! head -1 "yolov5s.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                    mv "yolov5s.hef.tmp" "yolov5s.hef"
                    size=$(stat -f%z "yolov5s.hef" 2>/dev/null || stat -c%s "yolov5s.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Detection model downloaded: yolov5s.hef ($size bytes)"
                    DETECTION_DOWNLOADED=1
                    break 2
                fi
            elif curl -L -f -s "$url" -o "yolov5s.hef.tmp" 2>/dev/null; then
                if [ -s "yolov5s.hef.tmp" ] && ! head -1 "yolov5s.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                    mv "yolov5s.hef.tmp" "yolov5s.hef"
                    size=$(stat -f%z "yolov5s.hef" 2>/dev/null || stat -c%s "yolov5s.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Detection model downloaded: yolov5s.hef ($size bytes)"
                    DETECTION_DOWNLOADED=1
                    break 2
                fi
            fi
            rm -f "yolov5s.hef.tmp"
        done
    done
    
    # If YOLOv5s failed, try SSD MobileNet v2 alternatives
    if [ $DETECTION_DOWNLOADED -eq 0 ]; then
        echo "Trying SSD MobileNet v2 fallback..."
        for branch in "${HAILO_BRANCHES[@]}"; do
            for path in "${ALTERNATIVE_DETECTION_PATHS[@]}"; do
                url="${HAILO_MODEL_ZOO_BASE}/${branch}/${path}"
                if wget -q --show-progress "$url" -O "ssd_mobilenet_v2_coco.hef.tmp" 2>&1; then
                    if [ -s "ssd_mobilenet_v2_coco.hef.tmp" ] && ! head -1 "ssd_mobilenet_v2_coco.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                        mv "ssd_mobilenet_v2_coco.hef.tmp" "ssd_mobilenet_v2_coco.hef"
                        size=$(stat -f%z "ssd_mobilenet_v2_coco.hef" 2>/dev/null || stat -c%s "ssd_mobilenet_v2_coco.hef" 2>/dev/null || echo "unknown")
                        echo "✓ Detection model downloaded: ssd_mobilenet_v2_coco.hef ($size bytes)"
                        DETECTION_DOWNLOADED=1
                        break 2
                    fi
                elif curl -L -f -s "$url" -o "ssd_mobilenet_v2_coco.hef.tmp" 2>/dev/null; then
                    if [ -s "ssd_mobilenet_v2_coco.hef.tmp" ] && ! head -1 "ssd_mobilenet_v2_coco.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                        mv "ssd_mobilenet_v2_coco.hef.tmp" "ssd_mobilenet_v2_coco.hef"
                        size=$(stat -f%z "ssd_mobilenet_v2_coco.hef" 2>/dev/null || stat -c%s "ssd_mobilenet_v2_coco.hef" 2>/dev/null || echo "unknown")
                        echo "✓ Detection model downloaded: ssd_mobilenet_v2_coco.hef ($size bytes)"
                        DETECTION_DOWNLOADED=1
                        break 2
                    fi
                fi
                rm -f "ssd_mobilenet_v2_coco.hef.tmp"
            done
        done
    fi
    
    if [ $DETECTION_DOWNLOADED -eq 0 ]; then
        echo ""
        echo "ERROR: Failed to download pre-compiled HEF model"
        echo ""
        echo "The Hailo Model Zoo should provide pre-compiled HEF files."
        echo "If downloads fail, try:"
        echo ""
        echo "  1. Check Raspberry Pi AI Kit examples:"
        echo "     https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
        echo ""
        echo "  2. Browse Model Zoo repository directly:"
        echo "     https://github.com/hailo-ai/hailo_model_zoo"
        echo "     Look for: hailo_models/<model>/hef/<model>.hef"
        echo ""
        echo "  3. Use Hailo Model Explorer:"
        echo "     https://hailo.ai/de/products/hailo-software/model-explorer-vision/"
        echo ""
        echo "CRITICAL: Service cannot run without a detection model!"
        exit 1
    fi
elif [ -f "yolov5s.hef" ] || [ -f "ssd_mobilenet_v2_coco.hef" ]; then
    echo "✓ Detection model already exists"
    DETECTION_DOWNLOADED=1
fi

# Download classification model (optional)
CLASSIFICATION_DOWNLOADED=0
if [ ! -f "mobilenet_v2_1.0_224_inat_bird.hef" ]; then
    echo "Downloading classification model (optional)..."
    for branch in "${HAILO_BRANCHES[@]}"; do
        for path in "${CLASSIFICATION_MODEL_PATHS[@]}"; do
            url="${HAILO_MODEL_ZOO_BASE}/${branch}/${path}"
            if wget -q --show-progress "$url" -O "mobilenet_v2_1.0_224_inat_bird.hef.tmp" 2>&1; then
                if [ -s "mobilenet_v2_1.0_224_inat_bird.hef.tmp" ] && ! head -1 "mobilenet_v2_1.0_224_inat_bird.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                    mv "mobilenet_v2_1.0_224_inat_bird.hef.tmp" "mobilenet_v2_1.0_224_inat_bird.hef"
                    size=$(stat -f%z "mobilenet_v2_1.0_224_inat_bird.hef" 2>/dev/null || stat -c%s "mobilenet_v2_1.0_224_inat_bird.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Classification model downloaded: mobilenet_v2_1.0_224_inat_bird.hef ($size bytes)"
                    CLASSIFICATION_DOWNLOADED=1
                    break 2
                fi
            elif curl -L -f -s "$url" -o "mobilenet_v2_1.0_224_inat_bird.hef.tmp" 2>/dev/null; then
                if [ -s "mobilenet_v2_1.0_224_inat_bird.hef.tmp" ] && ! head -1 "mobilenet_v2_1.0_224_inat_bird.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                    mv "mobilenet_v2_1.0_224_inat_bird.hef.tmp" "mobilenet_v2_1.0_224_inat_bird.hef"
                    size=$(stat -f%z "mobilenet_v2_1.0_224_inat_bird.hef" 2>/dev/null || stat -c%s "mobilenet_v2_1.0_224_inat_bird.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Classification model downloaded: mobilenet_v2_1.0_224_inat_bird.hef ($size bytes)"
                    CLASSIFICATION_DOWNLOADED=1
                    break 2
                fi
            fi
            rm -f "mobilenet_v2_1.0_224_inat_bird.hef.tmp"
        done
    done
    
    if [ $CLASSIFICATION_DOWNLOADED -eq 0 ]; then
        echo "⚠ Classification model not downloaded (optional)"
    fi
fi

# Download label files
echo "Downloading label files..."
if [ ! -f "coco_labels.txt" ]; then
    wget -q --show-progress "$COCO_LABELS_URL" -O "coco_labels.txt" || \
        wget -q --show-progress "https://raw.githubusercontent.com/tensorflow/models/master/research/object_detection/data/mscoco_label_map.pbtxt" -O "coco_labels.txt" || true
    [ -f "coco_labels.txt" ] && echo "✓ COCO labels downloaded"
fi

if [ ! -f "inat_bird_labels.txt" ]; then
    wget -q --show-progress "$INAT_BIRD_LABELS_URL" -O "inat_bird_labels.txt" || true
    [ -f "inat_bird_labels.txt" ] && echo "✓ iNaturalist bird labels downloaded"
fi

echo ""
echo "Summary:"
[ -f "yolov5s.hef" ] && echo "  ✓ yolov5s.hef" || [ -f "ssd_mobilenet_v2_coco.hef" ] && echo "  ✓ ssd_mobilenet_v2_coco.hef" || echo "  ✗ No detection model"
[ -f "mobilenet_v2_1.0_224_inat_bird.hef" ] && echo "  ✓ mobilenet_v2_1.0_224_inat_bird.hef" || echo "  ⚠ No classification model (optional)"
[ -f "coco_labels.txt" ] && echo "  ✓ coco_labels.txt" || echo "  ✗ No COCO labels"
[ -f "inat_bird_labels.txt" ] && echo "  ✓ inat_bird_labels.txt" || echo "  ✗ No bird labels"
echo ""
