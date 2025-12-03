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

### Service Management

The detection service runs as a systemd service. After installation, the service is **enabled** but **not started** automatically.

#### Start the Service

```bash
# Start the service
sudo systemctl start leroy.service

# Check service status
sudo systemctl status leroy.service

# View live logs
sudo journalctl -u leroy.service -f

# View recent logs (last boot)
sudo journalctl -u leroy.service -b
```

#### Enable Auto-Start on Boot

The service is automatically enabled during installation. To verify or manually enable:

```bash
# Enable service to start on boot
sudo systemctl enable leroy.service

# Verify it's enabled
sudo systemctl is-enabled leroy.service
```

#### Stop/Restart the Service

```bash
# Stop the service
sudo systemctl stop leroy.service

# Restart the service
sudo systemctl restart leroy.service

# Disable auto-start on boot (if needed)
sudo systemctl disable leroy.service
```

#### Service Behavior

- **Auto-updates**: The service automatically pulls the latest code from git when it starts (via `run.sh`)
- **Auto-restart**: The service is configured to restart automatically if it crashes (`Restart=on-abort`)
- **Logs**: All output is logged to systemd journal and `storage/results.log`

#### Manual Run (Testing)

For testing or debugging, you can run the detection script manually:

```bash
# Activate virtual environment
source venv/bin/activate

# Run detection script
python3 leroy.py

# Or with custom model/labels
python3 leroy.py --model all_models/yolov5s.hef --labels all_models/coco_labels.txt
```

### Configuration

Default model: Automatically uses `yolov5s.hef` if available (better accuracy), otherwise falls back to `ssd_mobilenet_v2_coco.hef` (HEF format for Hailo)

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

## Troubleshooting

### Service Won't Start

1. **Check service status**:
   ```bash
   sudo systemctl status leroy.service
   ```

2. **Check logs for errors**:
   ```bash
   sudo journalctl -u leroy.service -n 50
   ```

3. **Common issues**:
   - **Camera not found**: Ensure HQ Camera is connected and accessible
   - **Hailo SDK not found**: Verify AI Kit is properly installed
   - **Models missing**: Run `./download_models.sh` to download required models
   - **Virtual environment missing**: Re-run `./install-pi5.sh`

### Service Keeps Restarting

Check logs to identify the crash cause:
```bash
sudo journalctl -u leroy.service -f
```

Common causes:
- Camera initialization failure
- Hailo model loading error
- Missing dependencies

### View Detection Photos

Photos are stored in:
- **Detected (raw)**: `storage/detected/{date}/{visitation_id}/`
- **Classified**: `/var/www/html/classified/{date}/{visitation_id}/`
- **Web interface**: Visit `http://your-pi-ip/` (if web interface is built)

### Check Classification Status

Classification runs automatically via cron job (hourly). Check cron logs:
```bash
grep CRON /var/log/syslog
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
