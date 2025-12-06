# Project Leroy

Leroy is an AI birdwatcher built for Raspberry Pi 5 with AI Kit (Hailo).

## Hardware Requirements

- Raspberry Pi 5
- Raspberry Pi AI Kit (Hailo-8L accelerator)
- Raspberry Pi HQ Camera

## Installation

### 0. Enable Required Interfaces

Before running the install script, ensure these interfaces are enabled:

**Required Interfaces:**
- **Camera Interface**: Required for HQ Camera access
- **SSH**: Required for remote access and service management
- **PCIe**: Required for AI Kit (automatically configured by install script)

The install script will automatically enable Camera and SSH interfaces. If you prefer to enable them manually:

```bash
# Using raspi-config (recommended)
sudo raspi-config
# Navigate to: Interface Options → Camera → Enable
# Navigate to: Interface Options → SSH → Enable

# Or enable via command line
sudo raspi-config nonint do_camera 0
sudo raspi-config nonint do_ssh 0
```

**Note**: After enabling Camera interface, a reboot may be required.

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
- Enable required interfaces (Camera, SSH)
- Set up Python virtual environment
- Install system dependencies (Hailo SDK, rpicam-apps, nginx)
- Install Python packages
- Configure PCIe for AI Kit
- Configure systemd service
- Set up cron jobs
- Configure and start nginx
- Create storage directories
- Download HEF models (optional)

**Note**: All directories are created automatically when needed:
- `storage/detected/{date}/{visitation_id}/` - Created by `photo.py` when saving photos
- `/var/www/html/classified/{date}/{visitation_id}/` - Created by `classify.py` when moving files
- `storage/active_learning/*` - Created by `active_learning.py` on initialization

### 3. Download Models

Download pre-compiled HEF models from Hailo Model Zoo:

```bash
./download_models.sh
```

**Model Priority**:
- **Detection**: YOLOv5s (preferred) or SSD MobileNet v2 (fallback)
- **Classification**: MobileNet v2 (trained on 964 iNaturalist bird species)

Models are downloaded directly in HEF format - no conversion needed.

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

The service is automatically enabled during installation. To verify:

```bash
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

- **Auto-updates**: Pulls latest code from git when it starts (via `run.sh`)
- **Auto-restart**: Restarts automatically if it crashes (`Restart=on-abort`)
- **Auto-launch browser**: Launches browser with web app (if enabled, no duplicate windows)
- **Custom port**: Web interface runs on port **8080** (configurable)
- **Logs**: Output logged to systemd journal and `storage/results.log`

#### Configuration

Create or edit `leroy.env` to customize settings:

```bash
# Web Server Configuration
LEROY_WEB_PORT=8080          # Custom port (default: 8080)
LEROY_WEB_HOST=localhost     # Host (default: localhost)

# Browser Auto-Launch
LEROY_AUTO_LAUNCH_BROWSER=true  # Enable/disable (default: true)

# Camera Resolution Configuration
LEROY_DETECTION_WIDTH=1280   # Detection resolution width (default: 1280)
LEROY_DETECTION_HEIGHT=960   # Detection resolution height (default: 960)
LEROY_PHOTO_WIDTH=4056       # Photo resolution width (default: 4056)
LEROY_PHOTO_HEIGHT=3040      # Photo resolution height (default: 3040)
```

**Security Note**: Using port 8080 instead of 80/443 reduces exposure to automated scanners while remaining accessible on local network.

#### Manual Run (Testing)

For testing or debugging:

```bash
# Activate virtual environment
source venv/bin/activate

# Run detection script
python3 leroy.py

# Or with custom model/labels
python3 leroy.py --model all_models/yolov5s.hef --labels all_models/coco_labels.txt
```

**Default Model**: Automatically uses `yolov5s.hef` if available, otherwise falls back to `ssd_mobilenet_v2_coco.hef`.

## Architecture

- **Detection**: Configurable resolution (default: 1280x960), resized to 500px for inference
- **Photos**: Configurable high-resolution (default: 4056x3040) captured when birds are detected
- **Classification**: Runs periodically via cron job
- **Storage**: UUID-based filenames with JSON metadata for full scientific visitation schema support
- **Camera Resolution**: Configurable via `leroy.env` (LEROY_DETECTION_WIDTH/HEIGHT, LEROY_PHOTO_WIDTH/HEIGHT)

See `.cursor/rules/architecture.mdc` for detailed system architecture.

## Web Interface

The web interface is a lightweight vanilla JavaScript app (no build step required).

**On Raspberry Pi**: Nginx runs directly on the host (installed by `install-pi5.sh`). Access at `http://your-pi-ip:8080`.

**Local Development**: Use Docker for preview:
```bash
make web-preview
# Or: docker-compose -f docker-compose.nginx.yml up
```

See `web/README.md` for web interface details.

## Testing

Run tests using Docker (includes all dependencies):

```bash
# Option 1: Use test runner script (recommended)
./run_tests.sh                    # Run all tests
./run_tests.sh tests.test_visitation_processing  # Run specific test

# Option 2: Use Makefile
make docker-pi5-test              # Run all tests
make docker-pi5-test-file TEST=tests.test_visitation_processing  # Run specific test
```

**Note**: Tests focus on business logic. Hardware-dependent code (camera, Hailo) is not tested.

## Active Learning

The system can learn to identify new bird species not in the base model (964 iNaturalist species).

**Workflow**:
1. **Automatic Collection**: System collects low-confidence bird classifications
2. **Human Labeling**: Review and label unknown bird photos in `storage/active_learning/`
3. **Retraining**: Fine-tune model on new species data
4. **Deployment**: Update model and labels

**Quick Start**:
```bash
# After collecting and labeling unknown bird photos:
python3 retrain_model.py \
  --new_species_dir storage/active_learning/labeled/painted-bunting \
  --new_species_name painted-bunting \
  --new_class_id 965
```

## Social Media (Optional)

### Bluesky Posting

The system can optionally post to Bluesky with daily summaries.

**Setup**:
```bash
# Set environment variables in leroy.env
export BLUESKY_ENABLED=true
export BLUESKY_HANDLE=@your-handle.bsky.social
export BLUESKY_APP_PASSWORD=your-app-password
```

**Posting Rules**:
- **One post per day** - Single daily summary
- **Evening posting** - 7:00 PM - 9:00 PM
- **5 best photos** - Varying species, high clarity
- Only posts if authenticated, otherwise silently ignores

See `.cursor/rules/social-media-posting.mdc` for complete posting rules.

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

### Camera Diagnostics

**Quick Diagnostic Script:**
```bash
./diagnose_camera.sh
```

This script checks:
- Camera interface status
- Device detection (`/dev/video0`)
- Camera permissions
- OpenCV access
- Project Leroy camera manager

**Manual Camera Tests:**

1. **Check camera interface is enabled:**
   ```bash
   grep start_x /boot/firmware/config.txt
   # Should show: start_x=1
   ```

2. **Check camera device exists:**
   ```bash
   ls -l /dev/video*
   # Should show /dev/video0 with video group
   ```

3. **Test with v4l2-utils:**
   ```bash
   sudo apt-get install v4l-utils
   v4l2-ctl --device=/dev/video0 --all
   ```

4. **Test with rpicam (Raspberry Pi official tools):**
   ```bash
   sudo apt-get install rpicam-apps
   rpicam-hello  # 5 second preview
   rpicam-still -o test.jpg  # Capture test image
   ```

5. **Test with OpenCV (Python) - What Project Leroy uses:**
   ```bash
   # Quick test script
   python3 test_camera_opencv.py
   
   # Or manual test
   python3 << 'EOF'
   import cv2
   cap = cv2.VideoCapture(0)
   if cap.isOpened():
       ret, frame = cap.read()
       if ret:
           print(f"Camera working! Frame: {frame.shape[1]}x{frame.shape[0]}")
       else:
           print("Camera opened but can't read frames")
       cap.release()
   else:
       print("Failed to open camera")
   EOF
   ```

6. **Check user permissions:**
   ```bash
   groups  # Should include 'video'
   # If not: sudo usermod -aG video $USER
   # Then logout and login again
   ```

7. **Test with Project Leroy's camera manager:**
   ```bash
   python3 << 'EOF'
   from camera_manager import CameraManager
   camera = CameraManager(camera_idx=0)
   if camera.initialize():
       print("Camera manager initialized successfully")
       camera.release()
   else:
       print("Camera manager failed to initialize")
   EOF
   ```

**Common Camera Issues:**

- **Camera not detected**: Check cable connection, try different camera port
- **Permission denied**: Add user to video group: `sudo usermod -aG video $USER`
- **Interface not enabled**: Run `sudo raspi-config` → Interface Options → Camera → Enable
- **Wrong camera index**: Try different indices (0, 1, 2) with `--camera_idx` argument

### View Detection Photos

Photos are stored in:
- **Detected (raw)**: `storage/detected/{date}/{visitation_id}/`
- **Classified**: `/var/www/html/classified/{date}/{visitation_id}/`
- **Web interface**: Visit `http://your-pi-ip:8080/`

### Check Classification Status

Classification runs automatically via cron job (hourly). Check cron logs:
```bash
grep CRON /var/log/syslog
```

## Future Enhancements

- **iNaturalist Integration**: Planned feature to submit visitations to iNaturalist. Data format is already compatible - one observation per species per visitation.

## Additional Resources

- **Architecture**: `.cursor/rules/architecture.mdc` - Detailed system architecture
- **Web Interface**: `web/README.md` - Web app details
