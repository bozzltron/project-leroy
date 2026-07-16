#!/bin/bash
# Project Leroy - Model Download Helper Script
# 
# NOTE: HEF models must be downloaded manually from Hailo Model Explorer
# This script helps verify existing models and provides download instructions.

set -e

echo "Project Leroy - Model Verification and Download Helper"
echo "======================================================"
echo ""

MODELS_DIR="all_models"
mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

# Save script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment if available
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

echo "Checking for existing models..."
echo ""

# Check for detection model - try various YOLO versions
DETECTION_FOUND=0
if [ -f "detection_model.hef" ]; then
    size=$(stat -f%z "detection_model.hef" 2>/dev/null || stat -c%s "detection_model.hef" 2>/dev/null || echo "0")
    if [ "$size" != "0" ]; then
        echo "✓ Detection model found: detection_model.hef ($size bytes)"
        DETECTION_FOUND=1
    fi
fi

# Check for YOLO v11, v10, v8, v5, and SSD models
if [ $DETECTION_FOUND -eq 0 ]; then
    for model in "yolov11s.hef" "yolov10s.hef" "yolov8s.hef" "yolov5s.hef" "ssd_mobilenet_v2_coco.hef"; do
        if [ -f "$model" ]; then
            size=$(stat -f%z "$model" 2>/dev/null || stat -c%s "$model" 2>/dev/null || echo "0")
            if [ "$size" != "0" ]; then
                echo "✓ Detection model found: $model ($size bytes)"
                echo "  (Code will automatically use this model)"
                DETECTION_FOUND=1
                break
            fi
        fi
    done
fi

# Check system directories for detection models
if [ $DETECTION_FOUND -eq 0 ]; then
    echo "Checking system directories for detection models..."
    SYSTEM_MODEL=$(find /usr/share/rpi-camera-assets /opt/hailo /usr/share/hailo /usr/local/hailo -name "*.hef" -type f 2>/dev/null | grep -E "(yolo|ssd)" -i | grep -v classification | head -1)
    if [ -n "$SYSTEM_MODEL" ] && [ -f "$SYSTEM_MODEL" ]; then
        echo "Found system model: $SYSTEM_MODEL"
        cp "$SYSTEM_MODEL" "detection_model.hef"
        size=$(stat -f%z "detection_model.hef" 2>/dev/null || stat -c%s "detection_model.hef" 2>/dev/null || echo "unknown")
        echo "✓ Copied system model: detection_model.hef ($size bytes)"
        DETECTION_FOUND=1
    fi
fi

# Check for classification model - try MobileNet v3 first, then v2 variants
CLASSIFICATION_FOUND=0
for model in "mobilenet_v3.hef" "mobilenet_v2.hef"; do
    if [ -f "$model" ]; then
        size=$(stat -f%z "$model" 2>/dev/null || stat -c%s "$model" 2>/dev/null || echo "0")
        if [ "$size" = "0" ]; then
            echo "Removing zero-byte classification model file: $model"
            rm -f "$model"
        elif [ "$size" != "0" ]; then
            echo "✓ Classification model found: $model ($size bytes)"
            CLASSIFICATION_FOUND=1
            break
        fi
    fi
done

# Check system directories for classification models
if [ $CLASSIFICATION_FOUND -eq 0 ]; then
    echo "Checking system directories for classification models..."
    SYSTEM_CLASS_MODEL=$(find /usr/share/rpi-camera-assets /opt/hailo /usr/share/hailo /usr/local/hailo -name "*mobilenet*.hef" -type f 2>/dev/null | head -1)
    if [ -n "$SYSTEM_CLASS_MODEL" ] && [ -f "$SYSTEM_CLASS_MODEL" ]; then
        echo "Found system classification model: $SYSTEM_CLASS_MODEL"
        cp "$SYSTEM_CLASS_MODEL" "mobilenet_v3.hef"
        size=$(stat -f%z "mobilenet_v3.hef" 2>/dev/null || stat -c%s "mobilenet_v3.hef" 2>/dev/null || echo "unknown")
        echo "✓ Copied system classification model: mobilenet_v3.hef ($size bytes)"
        CLASSIFICATION_FOUND=1
    fi
fi

# Download label files (HEF models do NOT contain labels - they must be provided externally)
# yolo11s.txt and mobilenet_v3.txt are committed in-repo; no external label fetch is needed.
echo ""
echo "Downloading label files..."
echo ""

# MobileNet v3 ImageNet labels are maintained in-repo as mobilenet_v3.txt
# (iNaturalist bird labels are intentionally not fetched; the iNat HEF is not available.)

echo ""
echo "======================================================"
echo "Model Status Summary"
echo "======================================================"

# Summary - find and display detection model
DET_MODEL_FOUND=""
for model in "detection_model.hef" "yolov11s.hef" "yolov10s.hef" "yolov8s.hef" "yolov5s.hef" "ssd_mobilenet_v2_coco.hef"; do
    if [ -f "$model" ]; then
        size=$(stat -f%z "$model" 2>/dev/null || stat -c%s "$model" 2>/dev/null || echo "0")
        if [ "$size" != "0" ]; then
            DET_MODEL_FOUND="$model"
            break
        fi
    fi
done

if [ -n "$DET_MODEL_FOUND" ]; then
    size=$(stat -f%z "$DET_MODEL_FOUND" 2>/dev/null || stat -c%s "$DET_MODEL_FOUND" 2>/dev/null || echo "unknown")
    echo "✓ Detection model: $DET_MODEL_FOUND ($size bytes)"
else
    echo "✗ Detection model: MISSING (REQUIRED)"
fi

# Summary - find and display classification model
CLASS_MODEL_FOUND=""
for model in "mobilenet_v3.hef" "mobilenet_v2.hef"; do
    if [ -f "$model" ]; then
        size=$(stat -f%z "$model" 2>/dev/null || stat -c%s "$model" 2>/dev/null || echo "0")
        if [ "$size" != "0" ]; then
            CLASS_MODEL_FOUND="$model"
            break
        fi
    fi
done

if [ -n "$CLASS_MODEL_FOUND" ]; then
    size=$(stat -f%z "$CLASS_MODEL_FOUND" 2>/dev/null || stat -c%s "$CLASS_MODEL_FOUND" 2>/dev/null || echo "unknown")
    echo "✓ Classification model: $CLASS_MODEL_FOUND ($size bytes)"
else
    echo "✗ Classification model: MISSING (REQUIRED)"
fi

[ -f "yolo11s.txt" ] && echo "✓ COCO labels: yolo11s.txt" || echo "✗ COCO labels: yolo11s.txt MISSING"
[ -f "mobilenet_v3.txt" ] && echo "✓ Classification labels: mobilenet_v3.txt" || echo "✗ Classification labels: mobilenet_v3.txt MISSING"

echo ""

# If models are missing, provide download instructions
if [ $DETECTION_FOUND -eq 0 ] || [ $CLASSIFICATION_FOUND -eq 0 ]; then
    echo "======================================================"
    echo "Download Models from Hailo Model Explorer"
    echo "======================================================"
    echo ""
    echo "HEF models must be downloaded manually from Hailo Model Explorer:"
    echo ""
    echo "1. Visit: https://hailo.ai/products/hailo-software/model-explorer-vision/"
    echo "2. Sign in (create account if needed)"
    echo "3. Set filters:"
    echo "   - AI Processor: Hailo-8L"
    echo ""
    
    if [ $DETECTION_FOUND -eq 0 ]; then
        echo "4. For Detection Model:"
        echo "   - Task: Object Detection"
        echo "   - Recommended: YOLOv8s or YOLOv8m (best balance)"
        echo "   - Alternative: YOLOv5s or SSD MobileNet v2"
        echo "   - Download the COMPILED HEF file (not pretrained)"
        echo "   - Save as: detection_model.hef"
        echo ""
    fi
    
    if [ $CLASSIFICATION_FOUND -eq 0 ]; then
        echo "5. For Classification Model:"
        echo "   - Task: Classification"
        echo "   - Recommended: MobileNet v3 (ImageNet, ~59 bird species)"
        echo "   - Download the COMPILED HEF file"
        echo "   - Save as: mobilenet_v3.hef"
        echo "   - Note: MobileNet v2 iNaturalist bird (964 species) is not available as a pre-compiled HEF"
        echo ""
    fi
    
    echo "6. Copy downloaded HEF files to:"
    echo "   $(pwd)/"
    echo ""
    echo "7. Verify models:"
    echo "   ls -lh all_models/*.hef"
    echo ""
    echo "For more information, see README.md"
    echo ""
    
    if [ $DETECTION_FOUND -eq 0 ]; then
        echo "⚠ CRITICAL: Detection model is required for the service to run!"
        exit 1
    fi
fi

echo "======================================================"
echo "All required models found!"
echo "======================================================"
