#!/bin/bash
# Project Leroy - Model Conversion Script
# Converts TFLite models to HEF format using Hailo Dataflow Compiler

set -e

echo "=========================================="
echo "Project Leroy - Model Conversion Script"
echo "=========================================="
echo ""

MODELS_DIR="all_models"
cd "$MODELS_DIR"

# Check if Hailo Dataflow Compiler is available
if ! command -v hailo &> /dev/null && ! command -v hailo-dataflow-compiler &> /dev/null; then
    echo "ERROR: Hailo Dataflow Compiler not found!"
    echo ""
    echo "Please install Hailo Dataflow Compiler first:"
    echo "1. Follow official Raspberry Pi AI Kit installation guide"
    echo "2. Install hailo-dataflow-compiler package"
    echo "3. Or install from: https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
    echo ""
    exit 1
fi

# Determine DFC command
if command -v hailo-dataflow-compiler &> /dev/null; then
    DFC_CMD="hailo-dataflow-compiler"
elif command -v hailo &> /dev/null; then
    DFC_CMD="hailo"
else
    echo "ERROR: Could not find Hailo Dataflow Compiler"
    exit 1
fi

echo "Using: $DFC_CMD"
echo ""

# Detection model conversion
DETECTION_TFLITE="ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
DETECTION_HEF="ssd_mobilenet_v2_coco.hef"

if [ ! -f "$DETECTION_TFLITE" ]; then
    echo "ERROR: Detection model not found: $DETECTION_TFLITE"
    echo "Please run download_models.sh first"
    exit 1
fi

if [ -f "$DETECTION_HEF" ]; then
    echo "✓ Detection model already converted: $DETECTION_HEF"
else
    echo "Converting detection model..."
    echo "  Input: $DETECTION_TFLITE"
    echo "  Output: $DETECTION_HEF"
    echo ""
    
    # Note: The exact command syntax may vary based on Hailo DFC version
    # This is a template - adjust based on actual DFC documentation
    if $DFC_CMD compile \
        --input-format tflite \
        --input-path "$DETECTION_TFLITE" \
        --output-path "$DETECTION_HEF" \
        --target-device hailo8l 2>&1; then
        echo "✓ Detection model converted successfully"
    else
        echo ""
        echo "ERROR: Conversion failed!"
        echo ""
        echo "The exact DFC command syntax may vary. Try:"
        echo "  $DFC_CMD --help"
        echo ""
        echo "Or check official Hailo documentation for conversion command:"
        echo "  https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
        echo ""
        echo "Common alternative commands:"
        echo "  hailo dataflow compile -i $DETECTION_TFLITE -o $DETECTION_HEF"
        echo "  hailo-dataflow-compiler $DETECTION_TFLITE -o $DETECTION_HEF"
        exit 1
    fi
fi

echo ""

# Classification model conversion
CLASSIFICATION_TFLITE="mobilenet_v2_1.0_224_inat_bird_quant_postprocess_edgetpu.tflite"
CLASSIFICATION_HEF="mobilenet_v2_1.0_224_inat_bird.hef"

if [ ! -f "$CLASSIFICATION_TFLITE" ]; then
    echo "ERROR: Classification model not found: $CLASSIFICATION_TFLITE"
    echo "Please run download_models.sh first"
    exit 1
fi

if [ -f "$CLASSIFICATION_HEF" ]; then
    echo "✓ Classification model already converted: $CLASSIFICATION_HEF"
else
    echo "Converting classification model..."
    echo "  Input: $CLASSIFICATION_TFLITE"
    echo "  Output: $CLASSIFICATION_HEF"
    echo ""
    
    if $DFC_CMD compile \
        --input-format tflite \
        --input-path "$CLASSIFICATION_TFLITE" \
        --output-path "$CLASSIFICATION_HEF" \
        --target-device hailo8l 2>&1; then
        echo "✓ Classification model converted successfully"
    else
        echo ""
        echo "ERROR: Conversion failed!"
        echo ""
        echo "The exact DFC command syntax may vary. Try:"
        echo "  $DFC_CMD --help"
        echo ""
        echo "Or check official Hailo documentation for conversion command"
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "Model Conversion Complete!"
echo "=========================================="
echo ""
echo "Converted models:"
echo "  ✓ $DETECTION_HEF (Detection)"
echo "  ✓ $CLASSIFICATION_HEF (Classification)"
echo ""
echo "These HEF files are ready to use with leroy.py and classify.py"
echo ""

