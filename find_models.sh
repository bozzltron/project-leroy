#!/bin/bash
# Quick script to find any HEF files in the cloned Model Zoo

echo "Searching for HEF files in Model Zoo..."
echo ""

# Check local clone
MODEL_ZOO_PATH="$HOME/Projects/hailo_model_zoo"
if [ ! -d "$MODEL_ZOO_PATH" ]; then
    MODEL_ZOO_PATH="$HOME/hailo_model_zoo"
fi

if [ -d "$MODEL_ZOO_PATH" ]; then
    echo "Found Model Zoo at: $MODEL_ZOO_PATH"
    echo ""
    echo "All HEF files found:"
    find "$MODEL_ZOO_PATH" -name "*.hef" -type f 2>/dev/null | while read hef_file; do
        size=$(stat -c%s "$hef_file" 2>/dev/null || echo "unknown")
        echo "  $hef_file ($size bytes)"
    done
    echo ""
    
    # Look specifically in hailo_models
    echo "Detection models (in hailo_models/):"
    find "$MODEL_ZOO_PATH/hailo_models" -name "*.hef" -type f 2>/dev/null | grep -v mobilenet | grep -v classification | while read hef_file; do
        model_name=$(basename "$hef_file" .hef)
        size=$(stat -c%s "$hef_file" 2>/dev/null || echo "unknown")
        echo "  $model_name: $hef_file ($size bytes)"
    done
    echo ""
    
    # Check if any are COCO-compatible (usually YOLO or SSD models)
    echo "COCO-compatible models (YOLO/SSD - these work with coco_labels.txt):"
    COCO_MODELS=$(find "$MODEL_ZOO_PATH/hailo_models" -name "*.hef" -type f 2>/dev/null | grep -E "(yolo|ssd)" -i | grep -v classification)
    if [ -n "$COCO_MODELS" ]; then
        echo "$COCO_MODELS" | while read hef_file; do
            model_name=$(basename "$hef_file" .hef)
            size=$(stat -c%s "$hef_file" 2>/dev/null || echo "unknown")
            echo "  ✓ $model_name: $hef_file ($size bytes)"
            echo "    → Copy with: cp \"$hef_file\" ~/Projects/project-leroy/all_models/detection_model.hef"
        done
    else
        echo "  No COCO-compatible models found in hailo_models/"
        echo "  (HEF files may need to be compiled or downloaded from Hailo sources)"
    fi
else
    echo "Model Zoo not found at $MODEL_ZOO_PATH"
    echo ""
    echo "For the easiest way to get models, use Hailo Model Explorer:"
    echo "  https://hailo.ai/products/hailo-software/model-explorer-vision/"
    echo ""
    echo "Or clone Model Zoo: cd ~ && git clone --branch v2.15 https://github.com/hailo-ai/hailo_model_zoo.git"
fi

echo ""
echo "Also checking Hailo SDK installation directories:"
find /opt/hailo /usr/share/hailo /usr/local/hailo -name "*.hef" 2>/dev/null | head -5

echo ""
echo "Note: HEF files are typically not in the GitHub repository."
echo "Download pre-compiled HEF files from Hailo Model Explorer instead."

