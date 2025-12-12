#!/bin/bash
# Fix empty HEF model files by removing them and re-downloading

set -e

echo "=========================================="
echo "Fix Empty HEF Model Files"
echo "=========================================="
echo ""

MODELS_DIR="all_models"
cd "$MODELS_DIR"

# Check for empty HEF files
EMPTY_FILES=0
for hef_file in *.hef; do
    if [ -f "$hef_file" ]; then
        if [ ! -s "$hef_file" ]; then
            echo "⚠ Found empty file: $hef_file"
            rm -f "$hef_file"
            EMPTY_FILES=$((EMPTY_FILES + 1))
        else
            size=$(stat -f%z "$hef_file" 2>/dev/null || stat -c%s "$hef_file" 2>/dev/null || echo "unknown")
            echo "✓ Valid file: $hef_file ($size bytes)"
        fi
    fi
done

if [ $EMPTY_FILES -gt 0 ]; then
    echo ""
    echo "Removed $EMPTY_FILES empty HEF file(s)"
    echo ""
    echo "⚠ Empty files removed. Download models from Hailo Model Explorer:"
    echo "   https://hailo.ai/products/hailo-software/model-explorer-vision/"
    echo ""
    echo "After downloading, run: ./download_models.sh to verify"
else
    echo ""
    echo "✓ All HEF files are valid (non-empty)"
fi

