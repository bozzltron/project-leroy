#!/bin/bash
# Project Leroy - Model Verification Helper
#
# Detection: yolov11s.hef (HEF, Hailo-8L) — downloaded from Hailo Model Explorer
# Classification: species_classifier_nabirds.onnx (ONNX, CPU) — pre-downloaded, in all_models/

set -e

echo "Project Leroy - Model Verification"
echo "================================="
echo ""

MODELS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/all_models"
cd "$MODELS_DIR"

# Detection model
if [ -f "yolov11s.hef" ]; then
    size=$(stat -c%s "yolov11s.hef" 2>/dev/null || stat -f%z "yolov11s.hef" 2>/dev/null || echo "0")
    if [ "$size" -gt 0 ]; then
        echo "✓ Detection model: yolov11s.hef ($size bytes)"
    else
        echo "✗ Detection model yolov11s.hef is empty (0 bytes)"
    fi
else
    echo "✗ Detection model: MISSING (yolov11s.hef required)"
fi

# Classification model (ONNX, CPU)
if [ -f "species_classifier_nabirds.onnx" ]; then
    size=$(stat -c%s "species_classifier_nabirds.onnx" 2>/dev/null || stat -f%z "species_classifier_nabirds.onnx" 2>/dev/null || echo "0")
    if [ "$size" -gt 0 ]; then
        echo "✓ Classification model: species_classifier_nabirds.onnx ($size bytes)"
    else
        echo "✗ Classification model species_classifier_nabirds.onnx is empty (0 bytes)"
    fi
else
    echo "✗ Classification model: MISSING (species_classifier_nabirds.onnx required)"
fi

# Labels
[ -f "yolo11s.txt" ] && echo "✓ Detection labels: yolo11s.txt" || echo "✗ Detection labels: MISSING"
[ -f "nabirds_labels.txt" ] && echo "✓ Classification labels: nabirds_labels.txt" || echo "✗ Classification labels: MISSING"

echo ""
echo "Detection model must be downloaded from Hailo Model Explorer:"
echo "  Filter: AI Processor = Hailo-8L, Task = Object Detection"
echo "  Recommended: YOLOv11s (COMPILED HEF, not pretrained)"
echo ""
echo "Classification ONNX is pre-downloaded — no external fetch needed."
