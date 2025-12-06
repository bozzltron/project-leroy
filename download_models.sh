#!/bin/bash
# Project Leroy - Model Download Script
# Uses git sparse-checkout to efficiently download only HEF files from Model Zoo

set -e

echo "Downloading HEF models using git sparse-checkout..."

MODELS_DIR="all_models"
mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

# Check if git supports sparse-checkout (git 2.25+)
if ! git --version | grep -qE "git version [2-9]\.([2-9][0-9]|[3-9][0-9])"; then
    echo "Using fallback method (git sparse-checkout not available)..."
    USE_SPARSE_CHECKOUT=false
else
    USE_SPARSE_CHECKOUT=true
fi

# Hailo Model Zoo provides pre-compiled HEF files
# Primary source: Hailo S3 bucket (official pre-compiled models)
HAILO_S3_BASE="https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled"
HAILO_VERSIONS=("v2.15" "v2.14" "v2.13" "v2.12")

# Fallback: GitHub repository
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

# Method 1: Use git sparse-checkout (most efficient - only downloads HEF files)
if [ "$USE_SPARSE_CHECKOUT" = true ] && [ ! -f "yolov5s.hef" ] && [ ! -f "ssd_mobilenet_v2_coco.hef" ]; then
    echo "Using git sparse-checkout to download only HEF files..."
    TMP_DIR="/tmp/hailo_model_zoo_$$"
    rm -rf "$TMP_DIR"
    
    # Clone with sparse-checkout (only downloads HEF files, not entire repo)
    git clone --filter=blob:none --sparse --branch v2.15 --depth 1 \
        https://github.com/hailo-ai/hailo_model_zoo.git "$TMP_DIR" 2>/dev/null || {
        echo "Sparse checkout failed, trying full clone..."
        git clone --branch v2.15 --depth 1 \
            https://github.com/hailo-ai/hailo_model_zoo.git "$TMP_DIR" 2>/dev/null || {
            USE_SPARSE_CHECKOUT=false
        }
    }
    
    if [ -d "$TMP_DIR" ]; then
        cd "$TMP_DIR"
        
        if [ "$USE_SPARSE_CHECKOUT" = true ]; then
            git sparse-checkout init --cone 2>/dev/null || true
            git sparse-checkout set 'hailo_models/*/hef/*.hef' 2>/dev/null || true
        fi
        
        # Find and copy HEF files
        find hailo_models -name "*.hef" -type f 2>/dev/null | while read hef_file; do
            model_name=$(basename "$hef_file" .hef)
            if [[ "$model_name" == "yolov5s" ]]; then
                cp "$hef_file" "../../yolov5s.hef" 2>/dev/null && \
                    echo "✓ Downloaded: yolov5s.hef" && DETECTION_DOWNLOADED=1
            elif [[ "$model_name" == "ssd_mobilenet_v2" ]]; then
                cp "$hef_file" "../../ssd_mobilenet_v2_coco.hef" 2>/dev/null && \
                    echo "✓ Downloaded: ssd_mobilenet_v2_coco.hef" && DETECTION_DOWNLOADED=1
            elif [[ "$model_name" == "mobilenet_v2" ]]; then
                cp "$hef_file" "../../mobilenet_v2_1.0_224_inat_bird.hef" 2>/dev/null && \
                    echo "✓ Downloaded: mobilenet_v2_1.0_224_inat_bird.hef"
            fi
        done
        
        cd ../..
        rm -rf "$TMP_DIR"
    fi
fi

# Download detection model (YOLOv5s) - fallback methods
DETECTION_DOWNLOADED=0
if [ ! -f "yolov5s.hef" ] && [ ! -f "ssd_mobilenet_v2_coco.hef" ]; then
    echo "Downloading detection model..."
    
    # Method 2: Try Hailo S3 bucket (may require auth)
    for version in "${HAILO_VERSIONS[@]}"; do
        url="${HAILO_S3_BASE}/${version}/hailo8l/yolov5s.hef"
        if wget -q --show-progress "$url" -O "yolov5s.hef.tmp" 2>&1; then
            if [ -s "yolov5s.hef.tmp" ] && ! head -1 "yolov5s.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                mv "yolov5s.hef.tmp" "yolov5s.hef"
                size=$(stat -f%z "yolov5s.hef" 2>/dev/null || stat -c%s "yolov5s.hef" 2>/dev/null || echo "unknown")
                echo "✓ Detection model downloaded: yolov5s.hef ($size bytes)"
                DETECTION_DOWNLOADED=1
                break
            fi
        elif curl -L -f -s "$url" -o "yolov5s.hef.tmp" 2>/dev/null; then
            if [ -s "yolov5s.hef.tmp" ] && ! head -1 "yolov5s.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                mv "yolov5s.hef.tmp" "yolov5s.hef"
                size=$(stat -f%z "yolov5s.hef" 2>/dev/null || stat -c%s "yolov5s.hef" 2>/dev/null || echo "unknown")
                echo "✓ Detection model downloaded: yolov5s.hef ($size bytes)"
                DETECTION_DOWNLOADED=1
                break
            fi
        fi
        rm -f "yolov5s.hef.tmp"
    done
fi
    
    # If YOLOv5s failed, try SSD MobileNet v2 alternatives
    if [ $DETECTION_DOWNLOADED -eq 0 ]; then
        echo "Trying SSD MobileNet v2 fallback..."
        
        # Method 1: Try Hailo S3 bucket
        for version in "${HAILO_VERSIONS[@]}"; do
            url="${HAILO_S3_BASE}/${version}/hailo8l/ssd_mobilenet_v2.hef"
            if wget -q --show-progress "$url" -O "ssd_mobilenet_v2_coco.hef.tmp" 2>&1; then
                if [ -s "ssd_mobilenet_v2_coco.hef.tmp" ] && ! head -1 "ssd_mobilenet_v2_coco.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                    mv "ssd_mobilenet_v2_coco.hef.tmp" "ssd_mobilenet_v2_coco.hef"
                    size=$(stat -f%z "ssd_mobilenet_v2_coco.hef" 2>/dev/null || stat -c%s "ssd_mobilenet_v2_coco.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Detection model downloaded: ssd_mobilenet_v2_coco.hef ($size bytes)"
                    DETECTION_DOWNLOADED=1
                    break
                fi
            elif curl -L -f -s "$url" -o "ssd_mobilenet_v2_coco.hef.tmp" 2>/dev/null; then
                if [ -s "ssd_mobilenet_v2_coco.hef.tmp" ] && ! head -1 "ssd_mobilenet_v2_coco.hef.tmp" | grep -q "<!DOCTYPE\|<html"; then
                    mv "ssd_mobilenet_v2_coco.hef.tmp" "ssd_mobilenet_v2_coco.hef"
                    size=$(stat -f%z "ssd_mobilenet_v2_coco.hef" 2>/dev/null || stat -c%s "ssd_mobilenet_v2_coco.hef" 2>/dev/null || echo "unknown")
                    echo "✓ Detection model downloaded: ssd_mobilenet_v2_coco.hef ($size bytes)"
                    DETECTION_DOWNLOADED=1
                    break
                fi
            fi
            rm -f "ssd_mobilenet_v2_coco.hef.tmp"
        done
        
        # Method 2: Try GitHub repository (fallback)
        if [ $DETECTION_DOWNLOADED -eq 0 ]; then
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
    fi
    
    if [ $DETECTION_DOWNLOADED -eq 0 ]; then
        echo ""
        echo "ERROR: Failed to download detection model"
        echo ""
        echo "HEF files are not available via direct download (S3 requires auth)."
        echo ""
        echo "SOLUTION: You need to obtain HEF models manually:"
        echo ""
        echo "Option 1: Check if models are installed with Hailo SDK:"
        echo "  find /opt/hailo /usr/share/hailo /usr/local/hailo -name '*.hef' 2>/dev/null"
        echo ""
        echo "Option 2: Contact Hailo support or check Raspberry Pi AI Kit docs:"
        echo "  https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
        echo ""
        echo "Option 3: Use Hailo Model Explorer to download:"
        echo "  https://hailo.ai/de/products/hailo-software/model-explorer-vision/"
        echo ""
        echo "Option 4: If you have Hailo Dataflow Compiler, compile from Model Zoo:"
        echo "  git clone --branch v2.15 https://github.com/hailo-ai/hailo_model_zoo.git"
        echo "  cd hailo_model_zoo"
        echo "  pip install -e ."
        echo "  hailomz compile yolov5s --target hailo8l"
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
