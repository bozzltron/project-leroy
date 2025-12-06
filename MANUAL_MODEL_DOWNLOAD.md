# Manual HEF Model Download Commands

If the automated download script fails, use these manual commands to download HEF models directly from Hailo's S3 bucket.

## Detection Models (REQUIRED - choose one)

### Option 1: YOLOv5s (Recommended - better accuracy)

```bash
cd all_models

# Try latest version (v2.15)
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.15/hailo8l/yolov5s.hef

# If that fails, try v2.14
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14/hailo8l/yolov5s.hef

# If that fails, try v2.13
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13/hailo8l/yolov5s.hef
```

### Option 2: SSD MobileNet v2 (Fallback)

```bash
cd all_models

# Try latest version (v2.15)
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.15/hailo8l/ssd_mobilenet_v2.hef -O ssd_mobilenet_v2_coco.hef

# If that fails, try v2.14
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14/hailo8l/ssd_mobilenet_v2.hef -O ssd_mobilenet_v2_coco.hef

# If that fails, try v2.13
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

## Alternative: Clone Model Zoo Repository

If direct downloads fail, you can clone the repository and find HEF files:

```bash
# Clone the Model Zoo repository
git clone --branch v2.15 https://github.com/hailo-ai/hailo_model_zoo.git
cd hailo_model_zoo

# Search for HEF files
find . -name "*.hef" -type f | grep -E "(yolov5s|ssd_mobilenet|mobilenet_v2)" | head -10

# Copy found files to your project
cp <path_to_hef_file> ~/Projects/project-leroy/all_models/
```

## Notes

- **Hailo-8L**: Make sure you download models compiled for `hailo8l` (not `hailo8` or `hailo10`)
- **Version compatibility**: Use models from v2.13+ for best compatibility with current Hailo SDK
- **File sizes**: If a downloaded file is 0 bytes or very small (< 1KB), it's likely an error page - delete it and try again

