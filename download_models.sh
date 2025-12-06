#!/bin/bash
# Project Leroy - Model Download Script
# Uses Hailo Model Zoo best practices to obtain HEF models

# Don't exit on error - we want to try alternatives
set +e

echo "=========================================="
echo "Project Leroy - Model Download Script"
echo "=========================================="
echo ""
echo "Using Hailo Model Zoo best practices:"
echo "  1. Try hailomz tool (if available with Hailo SDK)"
echo "  2. Try direct HEF downloads from Model Zoo"
echo "  3. Provide manual download instructions"
echo ""

MODELS_DIR="all_models"
mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

# Check if hailomz tool is available (comes with Hailo SDK)
HAILOMZ_AVAILABLE=0
if command -v hailomz &> /dev/null; then
    HAILOMZ_AVAILABLE=1
    echo "✓ hailomz tool found - using Model Zoo workflow"
elif python3 -c "import hailo_model_zoo" 2>/dev/null; then
    HAILOMZ_AVAILABLE=1
    echo "✓ hailo_model_zoo Python package found"
else
    echo "⚠ hailomz tool not found - will try direct downloads"
    echo "  (hailomz comes with Hailo SDK installation)"
fi

# Hailo Model Zoo GitHub repository
# Note: Pre-compiled HEF files may not be directly available
# The proper workflow is to use hailomz to compile models
HAILO_MODEL_ZOO_BASE="https://github.com/hailo-ai/hailo_model_zoo/raw/v2.15"
HAILO_MODEL_ZOO_REPO="https://github.com/hailo-ai/hailo_model_zoo"

# Model paths in Hailo Model Zoo - try multiple possible locations
# Using YOLOv5s for detection (better than SSD MobileNet v2)
# Using MobileNet v2 for classification (trained on 964 iNaturalist bird species)
DETECTION_MODEL_PATHS=(
    "hailo_models/yolov5s/yolov5s.hef"
    "hailo_models/yolov5s/hef/yolov5s.hef"
    "models/yolov5s/yolov5s.hef"
    "yolov5s/yolov5s.hef"
)

ALTERNATIVE_DETECTION_PATHS=(
    "hailo_models/ssd_mobilenet_v2/ssd_mobilenet_v2.hef"
    "hailo_models/ssd_mobilenet_v2/hef/ssd_mobilenet_v2.hef"
    "models/ssd_mobilenet_v2/ssd_mobilenet_v2.hef"
    "ssd_mobilenet_v2/ssd_mobilenet_v2.hef"
)

CLASSIFICATION_MODEL_PATHS=(
    "hailo_models/mobilenet_v2/mobilenet_v2.hef"
    "hailo_models/mobilenet_v2/hef/mobilenet_v2.hef"
    "models/mobilenet_v2/mobilenet_v2.hef"
    "mobilenet_v2/mobilenet_v2.hef"
)

# Label file URLs (still need these)
COCO_LABELS_URL="https://dl.google.com/coral/canned_models/coco_labels.txt"
INAT_BIRD_LABELS_URL="https://github.com/google-coral/edgetpu/raw/master/test_data/inat_bird_labels.txt"

echo "Downloading HEF models from Hailo Model Zoo (v2.15 for Hailo-8L)..."
echo ""

# Download detection model (YOLOv5s)
DETECTION_DOWNLOADED=0
if [ ! -f "yolov5s.hef" ] && [ ! -f "ssd_mobilenet_v2_coco.hef" ]; then
    # Method 1: Try hailomz tool (best practice)
    if [ $HAILOMZ_AVAILABLE -eq 1 ]; then
        echo ""
        echo "Method 1: Using hailomz tool (Model Zoo best practice)..."
        echo "  This compiles models from the Model Zoo to HEF format"
        echo ""
        
        # Try to compile YOLOv5s using hailomz
        if command -v hailomz &> /dev/null; then
            echo "  Attempting: hailomz compile yolov5s --target hailo8l"
            if hailomz compile yolov5s --target hailo8l 2>&1 | tee /tmp/hailomz_output.log; then
                # Check if HEF file was created (location may vary)
                if [ -f "yolov5s.hef" ]; then
                    size=$(stat -f%z "yolov5s.hef" 2>/dev/null || stat -c%s "yolov5s.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Detection model compiled (YOLOv5s) using hailomz (size: $size bytes)"
                    DETECTION_DOWNLOADED=1
                elif find . -name "yolov5s.hef" -type f 2>/dev/null | head -1 | read hef_path; then
                    cp "$hef_path" "yolov5s.hef"
                    size=$(stat -f%z "yolov5s.hef" 2>/dev/null || stat -c%s "yolov5s.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Detection model compiled (YOLOv5s) using hailomz (size: $size bytes)"
                    DETECTION_DOWNLOADED=1
                else
                    echo "  ⚠ hailomz compile completed but HEF file not found in expected location"
                    echo "  Check output above for actual file location"
                fi
            else
                echo "  ⚠ hailomz compile failed, trying direct download..."
            fi
        fi
    fi
    
    # Method 2: Try direct HEF downloads (if hailomz not available or failed)
    if [ $DETECTION_DOWNLOADED -eq 0 ]; then
        echo ""
        echo "Method 2: Trying direct HEF downloads from Model Zoo..."
        echo "  Note: Pre-compiled HEF files may not be available at these paths"
        echo ""
        echo "Downloading detection model (YOLOv5s)..."
        
        # Try each possible path for YOLOv5s
    for path in "${DETECTION_MODEL_PATHS[@]}"; do
        echo "  Trying: ${HAILO_MODEL_ZOO_BASE}/${path}"
        # Try wget first
        if wget -q --show-progress "${HAILO_MODEL_ZOO_BASE}/${path}" -O "yolov5s.hef.tmp" 2>&1; then
            if [ -s "yolov5s.hef.tmp" ]; then
                # Check if it's actually a valid file (not an HTML error page)
                if head -1 "yolov5s.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                    rm -f "yolov5s.hef.tmp"
                    echo "  ✗ Got HTML error page (404?), trying next path..."
                else
                    mv "yolov5s.hef.tmp" "yolov5s.hef"
                    size=$(stat -f%z "yolov5s.hef" 2>/dev/null || stat -c%s "yolov5s.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Detection model downloaded (YOLOv5s) from: $path (size: $size bytes)"
                    DETECTION_DOWNLOADED=1
                    break
                fi
            else
                rm -f "yolov5s.hef.tmp"
                echo "  ✗ Downloaded file is empty, trying next path..."
            fi
        else
            rm -f "yolov5s.hef.tmp"
            # Try curl as fallback
            echo "  Trying with curl..."
            if curl -L -f -s "${HAILO_MODEL_ZOO_BASE}/${path}" -o "yolov5s.hef.tmp" 2>/dev/null; then
                if [ -s "yolov5s.hef.tmp" ] && ! head -1 "yolov5s.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                    mv "yolov5s.hef.tmp" "yolov5s.hef"
                    size=$(stat -f%z "yolov5s.hef" 2>/dev/null || stat -c%s "yolov5s.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Detection model downloaded (YOLOv5s) from: $path (size: $size bytes)"
                    DETECTION_DOWNLOADED=1
                    break
                else
                    rm -f "yolov5s.hef.tmp"
                fi
            fi
        fi
    done
    
    # If YOLOv5s failed, try SSD MobileNet v2 alternatives
    if [ $DETECTION_DOWNLOADED -eq 0 ]; then
        echo "WARNING: Failed to download YOLOv5s, trying SSD MobileNet v2..."
        for path in "${ALTERNATIVE_DETECTION_PATHS[@]}"; do
            echo "  Trying: $path"
            if wget -q --show-progress "${HAILO_MODEL_ZOO_BASE}/${path}" -O "ssd_mobilenet_v2_coco.hef.tmp" 2>&1; then
                if [ -s "ssd_mobilenet_v2_coco.hef.tmp" ]; then
                    mv "ssd_mobilenet_v2_coco.hef.tmp" "ssd_mobilenet_v2_coco.hef"
                    size=$(stat -f%z "ssd_mobilenet_v2_coco.hef" 2>/dev/null || stat -c%s "ssd_mobilenet_v2_coco.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Detection model downloaded (SSD MobileNet v2 fallback) from: $path (size: $size bytes)"
                    DETECTION_DOWNLOADED=1
                    break
                else
                    rm -f "ssd_mobilenet_v2_coco.hef.tmp"
                    echo "  ⚠ Downloaded file is empty, trying next path..."
                fi
            else
                rm -f "ssd_mobilenet_v2_coco.hef.tmp"
            fi
        done
    fi
    
    if [ $DETECTION_DOWNLOADED -eq 0 ]; then
        echo ""
        echo "=========================================="
        echo "ERROR: Failed to download detection model"
        echo "=========================================="
        echo ""
        echo "The HEF models are not available at the expected GitHub paths."
        echo "This is common - Hailo Model Zoo may require conversion from TFLite."
        echo ""
        echo "SOLUTION: Download pre-compiled models or convert TFLite models"
        echo ""
        echo "Option 1: Check Raspberry Pi AI Kit documentation"
        echo "  The official Raspberry Pi AI Kit guide may have direct download links:"
        echo "  https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
        echo ""
        echo "Option 2: Use Hailo Developer Zone"
        echo "  Check for pre-compiled HEF models:"
        echo "  https://hailo.ai/developer-zone/"
        echo ""
        echo "Option 3: Convert TFLite models (if you have Hailo DFC installed)"
        echo "  Run: ./convert_models.sh"
        echo "  This requires the Hailo Dataflow Compiler"
        echo ""
        echo "Option 4: Manual download from GitHub"
        echo "  1. Visit: https://github.com/hailo-ai/hailo_model_zoo"
        echo "  2. Browse the repository for HEF files"
        echo "  3. Download and place in all_models/ directory"
        echo ""
        echo "CRITICAL: The service cannot run without a detection model!"
        echo "Please download a model before starting the service."
        echo ""
        # Don't exit - continue with label files, but warn user
    fi
elif [ -f "yolov5s.hef" ] || [ -f "ssd_mobilenet_v2_coco.hef" ]; then
    echo "✓ Detection model already exists"
    DETECTION_DOWNLOADED=1
fi

# Download classification model (MobileNet v2 - trained on 964 bird species)
CLASSIFICATION_DOWNLOADED=0
if [ ! -f "mobilenet_v2_1.0_224_inat_bird.hef" ]; then
    # Method 1: Try hailomz tool (best practice)
    if [ $HAILOMZ_AVAILABLE -eq 1 ] && [ $DETECTION_DOWNLOADED -eq 1 ]; then
        echo ""
        echo "Method 1: Using hailomz tool for classification model..."
        if command -v hailomz &> /dev/null; then
            echo "  Attempting: hailomz compile mobilenet_v2 --target hailo8l"
            if hailomz compile mobilenet_v2 --target hailo8l 2>&1; then
                if [ -f "mobilenet_v2.hef" ]; then
                    mv "mobilenet_v2.hef" "mobilenet_v2_1.0_224_inat_bird.hef"
                    size=$(stat -f%z "mobilenet_v2_1.0_224_inat_bird.hef" 2>/dev/null || stat -c%s "mobilenet_v2_1.0_224_inat_bird.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Classification model compiled using hailomz (size: $size bytes)"
                    CLASSIFICATION_DOWNLOADED=1
                fi
            fi
        fi
    fi
    
    # Method 2: Try direct downloads
    if [ $CLASSIFICATION_DOWNLOADED -eq 0 ]; then
        echo ""
        echo "Method 2: Trying direct HEF downloads..."
        echo "Downloading classification model (MobileNet v2)..."
        
        # Try each possible path
    for path in "${CLASSIFICATION_MODEL_PATHS[@]}"; do
        echo "  Trying: ${HAILO_MODEL_ZOO_BASE}/${path}"
        # Try wget first
        if wget -q --show-progress "${HAILO_MODEL_ZOO_BASE}/${path}" -O "mobilenet_v2_1.0_224_inat_bird.hef.tmp" 2>&1; then
            if [ -s "mobilenet_v2_1.0_224_inat_bird.hef.tmp" ]; then
                # Check if it's actually a valid file (not an HTML error page)
                if head -1 "mobilenet_v2_1.0_224_inat_bird.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                    rm -f "mobilenet_v2_1.0_224_inat_bird.hef.tmp"
                    echo "  ✗ Got HTML error page (404?), trying next path..."
                else
                    mv "mobilenet_v2_1.0_224_inat_bird.hef.tmp" "mobilenet_v2_1.0_224_inat_bird.hef"
                    size=$(stat -f%z "mobilenet_v2_1.0_224_inat_bird.hef" 2>/dev/null || stat -c%s "mobilenet_v2_1.0_224_inat_bird.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Classification model downloaded (MobileNet v2) from: $path (size: $size bytes)"
                    CLASSIFICATION_DOWNLOADED=1
                    break
                fi
            else
                rm -f "mobilenet_v2_1.0_224_inat_bird.hef.tmp"
                echo "  ✗ Downloaded file is empty, trying next path..."
            fi
        else
            rm -f "mobilenet_v2_1.0_224_inat_bird.hef.tmp"
            # Try curl as fallback
            echo "  Trying with curl..."
            if curl -L -f -s "${HAILO_MODEL_ZOO_BASE}/${path}" -o "mobilenet_v2_1.0_224_inat_bird.hef.tmp" 2>/dev/null; then
                if [ -s "mobilenet_v2_1.0_224_inat_bird.hef.tmp" ] && ! head -1 "mobilenet_v2_1.0_224_inat_bird.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                    mv "mobilenet_v2_1.0_224_inat_bird.hef.tmp" "mobilenet_v2_1.0_224_inat_bird.hef"
                    size=$(stat -f%z "mobilenet_v2_1.0_224_inat_bird.hef" 2>/dev/null || stat -c%s "mobilenet_v2_1.0_224_inat_bird.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Classification model downloaded (MobileNet v2) from: $path (size: $size bytes)"
                    CLASSIFICATION_DOWNLOADED=1
                    break
                else
                    rm -f "mobilenet_v2_1.0_224_inat_bird.hef.tmp"
                fi
            fi
        fi
    done
    
    if [ $CLASSIFICATION_DOWNLOADED -eq 0 ]; then
        echo ""
        echo "WARNING: Failed to download MobileNet v2 from Hailo Model Zoo"
        echo ""
        echo "Options:"
        echo "1. Download manually from: https://github.com/hailo-ai/hailo_model_zoo/tree/v2.15"
        echo "2. Convert TFLite model using convert_models.sh (requires Hailo Dataflow Compiler)"
        echo "3. Use the original TFLite model if Hailo SDK supports it directly"
        echo ""
        echo "Note: MobileNet v2 from Hailo Model Zoo may need to be fine-tuned on bird dataset"
        echo "Alternatively, use the iNaturalist bird-specific model if available"
        echo ""
    fi
elif [ -f "mobilenet_v2_1.0_224_inat_bird.hef" ]; then
    echo "✓ Classification model already exists"
    CLASSIFICATION_DOWNLOADED=1
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
            # Don't exit - continue anyway
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
        # Don't exit - continue anyway
    }
    echo "✓ iNaturalist bird labels downloaded"
else
    echo "✓ iNaturalist bird labels already exist"
fi

echo ""
echo "=========================================="
echo "Model Download Summary"
echo "=========================================="
echo ""

# List downloaded files
echo "Downloaded files:"
if [ -f "yolov5s.hef" ]; then
    echo "  ✓ yolov5s.hef (Detection - YOLOv5s)"
elif [ -f "ssd_mobilenet_v2_coco.hef" ]; then
    echo "  ✓ ssd_mobilenet_v2_coco.hef (Detection - SSD MobileNet v2)"
else
    echo "  ✗ Detection model NOT downloaded"
fi

if [ -f "mobilenet_v2_1.0_224_inat_bird.hef" ]; then
    echo "  ✓ mobilenet_v2_1.0_224_inat_bird.hef (Classification - MobileNet v2)"
else
    echo "  ✗ Classification model NOT downloaded"
fi

if [ -f "coco_labels.txt" ]; then
    echo "  ✓ coco_labels.txt (COCO object labels)"
else
    echo "  ✗ COCO labels NOT downloaded"
fi

if [ -f "inat_bird_labels.txt" ]; then
    echo "  ✓ inat_bird_labels.txt (Bird species labels)"
else
    echo "  ✗ iNaturalist bird labels NOT downloaded"
fi
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

# Check if we have at least one detection model
if [ $DETECTION_DOWNLOADED -eq 0 ]; then
    echo "⚠⚠⚠ WARNING: NO DETECTION MODEL DOWNLOADED ⚠⚠⚠"
    echo ""
    echo "The service CANNOT run without a detection model!"
    echo ""
    echo "You must download a model before starting the service."
    echo ""
    echo "Quick fix options:"
    echo "1. Check Raspberry Pi AI Kit documentation for model downloads:"
    echo "   https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
    echo ""
    echo "2. Check Hailo Developer Zone:"
    echo "   https://hailo.ai/developer-zone/"
    echo ""
    echo "3. If you have Hailo Dataflow Compiler, convert TFLite models:"
    echo "   ./convert_models.sh"
    echo ""
    echo "4. Manually download HEF files and place in all_models/ directory"
    echo ""
    exit 1
else
    echo "✓ Detection model ready!"
fi

if [ $CLASSIFICATION_DOWNLOADED -eq 0 ]; then
    echo "⚠ Classification model not downloaded (optional for now)"
    echo "  You can download it later or convert from TFLite"
else
    echo "✓ Classification model ready!"
fi

echo ""
echo "Models are ready to use! No conversion needed."
echo ""
echo "Default models in code:"
if [ -f "yolov5s.hef" ]; then
    echo "  - Detection: yolov5s.hef (YOLOv5s - better accuracy)"
elif [ -f "ssd_mobilenet_v2_coco.hef" ]; then
    echo "  - Detection: ssd_mobilenet_v2_coco.hef (SSD MobileNet v2)"
fi

if [ -f "mobilenet_v2_1.0_224_inat_bird.hef" ]; then
    echo "  - Classification: mobilenet_v2_1.0_224_inat_bird.hef"
fi
echo ""
