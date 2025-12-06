# Manual HEF Model Download Commands

If the automated download script fails, use these methods to get HEF models.

**Note**: The S3 bucket may require authentication. Use Method 1 (clone repository) for the most reliable approach.

## Method 1: Clone Model Zoo Repository (RECOMMENDED)

This is the most reliable method - clone the repository and find HEF files:

```bash
# Clone the Model Zoo repository (v2.15 branch for Hailo-8L)
cd ~
git clone --branch v2.15 --depth 1 https://github.com/hailo-ai/hailo_model_zoo.git
cd hailo_model_zoo

# Search for YOLOv5s HEF file
find . -name "yolov5s.hef" -type f

# Search for SSD MobileNet v2 HEF file
find . -name "*ssd_mobilenet*.hef" -type f

# Search for MobileNet v2 HEF file
find . -name "mobilenet_v2.hef" -type f

# Once you find the files, copy them to your project
# Example (adjust path based on find results):
cp hailo_models/yolov5s/hef/yolov5s.hef ~/Projects/project-leroy/all_models/
cp hailo_models/ssd_mobilenet_v2/hef/ssd_mobilenet_v2.hef ~/Projects/project-leroy/all_models/ssd_mobilenet_v2_coco.hef
```

## Method 2: Try S3 Bucket (May require authentication)

The S3 bucket may return 403 Forbidden. If it works, use these URLs:

### YOLOv5s (Recommended)

```bash
cd all_models

# Try different versions
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14/hailo8l/yolov5s.hef
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13/hailo8l/yolov5s.hef
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.12/hailo8l/yolov5s.hef
```

### SSD MobileNet v2 (Fallback)

```bash
cd all_models

wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14/hailo8l/ssd_mobilenet_v2.hef -O ssd_mobilenet_v2_coco.hef
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13/hailo8l/ssd_mobilenet_v2.hef -O ssd_mobilenet_v2_coco.hef
```

## Classification Model (Optional)

```bash
cd all_models

# MobileNet v2 (you may need to fine-tune this for birds)
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.15/hailo8l/mobilenet_v2.hef -O mobilenet_v2_1.0_224_inat_bird.hef
```

## Label Files (Required)

```bash
cd all_models

# COCO labels (for detection)
wget https://dl.google.com/coral/canned_models/coco_labels.txt

# iNaturalist bird labels (for classification)
wget https://github.com/google-coral/edgetpu/raw/master/test_data/inat_bird_labels.txt
```

## Verify Downloads

```bash
cd all_models
ls -lh *.hef *.txt

# Check file sizes (should be > 0 bytes)
# YOLOv5s: ~5-10 MB
# SSD MobileNet v2: ~2-5 MB
# MobileNet v2: ~1-3 MB
```

## Method 3: Check Hailo SDK Installation

Sometimes example models are included with the Hailo SDK:

```bash
# Check if models are installed with SDK
find /opt/hailo -name "*.hef" 2>/dev/null
find /usr/share/hailo -name "*.hef" 2>/dev/null
find /usr/local/hailo -name "*.hef" 2>/dev/null

# If found, copy to project
cp <found_hef_file> ~/Projects/project-leroy/all_models/
```

## Method 4: Use Hailo Model Explorer

1. Visit: https://hailo.ai/de/products/hailo-software/model-explorer-vision/
2. Filter by: Device = Hailo-8L, Task = Object Detection
3. Find YOLOv5s or SSD MobileNet v2
4. Download the HEF file directly from the interface
5. Copy to `all_models/` directory

## Notes

- **Hailo-8L**: Make sure you download models compiled for `hailo8l` (not `hailo8` or `hailo10`)
- **Version compatibility**: Use models from v2.13+ for best compatibility with current Hailo SDK
- **File sizes**: If a downloaded file is 0 bytes or very small (< 1KB), it's likely an error page - delete it and try again

