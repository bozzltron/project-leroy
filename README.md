# Project Leroy

Leroy is an AI birdwatcher built for Raspberry Pi 5 with AI Kit (Hailo).

## Hardware Requirements

- Raspberry Pi 5
- Raspberry Pi AI Kit (Hailo-8L accelerator)
- Raspberry Pi HQ Camera

## Installation

### 1. Clone Repository

```bash
git clone <repository-url> project-leroy
cd project-leroy
```

### 2. Run Installation Script

```bash
./install-pi5.sh
```

This will:
- Set up Python virtual environment
- Install system dependencies (Hailo SDK, rpicam-apps)
- Install Python packages
- Configure systemd service
- Set up cron jobs
- Download HEF models (optional)

### 3. Download Models

**Download HEF Models from Hailo Model Zoo**
```bash
# Download pre-compiled HEF models (no conversion needed)
./download_models.sh
```

**Note**: 
- Models are downloaded directly from Hailo Model Zoo in HEF format
- YOLOv5s (detection) and EfficientNet-B0 (classification) are preferred
- Falls back to SSD MobileNet v2 and MobileNet v2 if preferred models unavailable

## Usage

### Run Detection Service

The service runs automatically via systemd:

```bash
sudo systemctl start leroy.service
sudo systemctl status leroy.service
```

Or run manually:

```bash
python3 leroy.py
```

### Configuration

Default model: `ssd_mobilenet_v2_coco.hef` (HEF format for Hailo)

You can change the model and labels using flags:

```bash
python3 leroy.py --model all_models/your_model.hef --labels all_models/your_labels.txt
```

## Architecture

- **Detection**: 1.2MP (1280x960) frames, resized to 500px for inference
- **Photos**: 12MP (4056x3040) captured when birds are detected
- **Classification**: Runs periodically via cron job

See `architecture.mdc` for detailed system architecture.

## Testing

Run tests using Docker (includes all dependencies like cv2):

```bash
# Option 1: Use test runner script (recommended)
./run_tests.sh                    # Run all tests
./run_tests.sh tests.test_visitation_processing  # Run specific test

# Option 2: Use Makefile
make docker-pi5-build            # Build Docker image
make docker-pi5-test              # Run all tests
make docker-pi5-test-file TEST=tests.test_visitation_processing  # Run specific test

# Option 3: Direct Docker command
docker-compose -f docker-compose.pi5.yml run --rm leroy-pi5 bash -c \
    "cd /app && source venv/bin/activate && python3 -m unittest discover tests -v"
```

## Active Learning: Adding New Bird Species

The system can learn to identify new bird species not in the base model (964 iNaturalist species).

**Workflow**:
1. **Automatic Collection**: System collects low-confidence bird classifications
2. **Human Labeling**: Review and label unknown bird photos
3. **Retraining**: Fine-tune model on new species data
4. **Deployment**: Update model and labels

**See `NEW_SPECIES_WALKTHROUGH.md` for detailed walkthrough.**

**Quick Start**:
```bash
# After collecting unknown bird photos and labeling them:
python3 retrain_model.py \
  --new_species_dir storage/active_learning/labeled/painted-bunting \
  --new_species_name painted-bunting \
  --new_class_id 965
```

## Testing

Run tests (optional, minimal test suite):

```bash
pytest tests/
```

**Note**: Tests focus on business logic. Hardware-dependent code (camera, Hailo) is not tested.

## Social Media (Optional)

### Bluesky Posting

The system can optionally post to Bluesky with daily summaries and special visitations.

**Setup**:
```bash
# Set environment variables
export BLUESKY_ENABLED=true
export BLUESKY_HANDLE=@your-handle.bsky.social
export BLUESKY_APP_PASSWORD=your-app-password

# Or add to service/leroy.env
```

**Posting Rules**:
- **One post per day** - Single daily summary
- **Evening posting** - 7:00 PM - 9:00 PM (captures full day's activity)
- **5 best photos** - Varying species, high clarity
- Only posts if authenticated, otherwise silently ignores

**See**: `.cursor/rules/social-media-posting.mdc` for complete posting rules
