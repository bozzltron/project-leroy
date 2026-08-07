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
- Set up cron jobs (classification every 30 minutes, runs as root via /etc/cron.d/leroy-classify)
- Configure log rotation for storage/results.log and /var/log/leroy-classify.log (daily, 100M size trigger, 7 retained)
- Configure and start nginx
- Create storage directories
- Check for HEF models (models must be downloaded from Hailo Model Explorer)

**Note**: All directories are created automatically when needed:
- `storage/detected/{date}/{visitation_id}/` - Created by `photo.py` when saving photos
- `/var/www/html/classified/{date}/{visitation_id}/` - Created by `classify.py` when moving files
- `storage/active_learning/*` - Created by `active_learning.py` on initialization

### 3. Download Models

**CRITICAL**: The service requires both detection and classification models to run.

HEF models must be downloaded manually from **Hailo Model Explorer**:

1. **Visit Hailo Model Explorer**:
   - https://hailo.ai/products/hailo-software/model-explorer-vision/
   - Sign in (create account if needed)

2. **Download Detection Model** (REQUIRED):
   - **CRITICAL**: Filter by AI Processor = **Hailo-8L** (NOT Hailo-8 or Hailo-10)
   - Task = **Object Detection**
   - Recommended: **YOLOv11s**
   - Download the **COMPILED HEF** file (not pretrained)
   - **Verify**: Model description should mention "Hailo-8L" or "hailo8l"
   - Save as: `yolov11s.hef`
   - **⚠️ If you get "HEF_NOT_COMPATIBLE" error**: The model was compiled for wrong device - delete it and download Hailo-8L version

3. **Download Classification Model** (REQUIRED):
   - **Classification runs via ONNX Runtime on CPU** — no Hailo HEF needed.
   - The Ornimetrics NABirds 555-species ONNX model is pre-downloaded in `all_models/`.
   - See `leroy.env.example` for configuration (LEROY_CLASSIFICATION_MODEL/LABELS).

> **Note**: HEF classification models compiled for Hailo-8 (26 TOPS) are **NOT**
> compatible with the Pi AI Kit's Hailo-8L (13 TOPS). Use ONNX for classification.

4. **Copy Models to Project**:
   ```bash
   # Copy downloaded HEF files to all_models/ directory
   # Detection model (use the actual filename you downloaded):
    cp ~/Downloads/yolov11s.hef all_models/
   
   # Classification model is pre-downloaded ONNX (no copy needed)
   ```

5. **Verify Models**:
   ```bash
   ./download_models.sh
   # This script verifies models and downloads label files
   # It will show which models were detected and their file sizes
   ```

**Example Output** (after downloading models):
```bash
$ ./download_models.sh
✓ Detection model found: yolov11s.hef (25565440 bytes)
✓ Classification model found: species_classifier_nabirds.onnx (83382384 bytes)
✓ COCO labels: yolo11s.txt
✓ Classification labels: nabirds_labels.txt
```

**Model Requirements**:
- **Detection**: COCO-compatible model (detects 80 classes including 'bird') - **REQUIRED**
  - Supported model: YOLOv11s (HEF, compiled for Hailo-8L)
- **Classification**: Ornimetrics NABirds 555-species - **REQUIRED**
  - Pre-downloaded ONNX model (CPU via ONNX Runtime)
  - Active config: `LEROY_CLASSIFICATION_MODEL=all_models/species_classifier_nabirds.onnx`

All HEF files should show non-zero file sizes. If any are 0 bytes, remove them:
```bash
./fix_empty_models.sh
```
Then download valid models from Hailo Model Explorer.

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
```

#### Update Code

To pull latest code and redeploy the web interface:

```bash
./update.sh
sudo systemctl restart leroy.service
```

#### Disable Auto-Start on Boot

```bash
sudo systemctl disable leroy.service
```

#### Service Behavior

- **Updates**: Run `./update.sh` to pull code and deploy web; then restart service
- **Auto-restart**: Restarts automatically if it crashes (`Restart=on-failure`)
- **Auto-launch browser**: Launches browser with web app (if enabled, no duplicate windows)
- **Custom port**: Web interface runs on port **80** (configurable)
- **Logs**: Output logged to systemd journal and `storage/results.log`

#### Configuration

Create or edit `leroy.env` to customize settings:

```
# Detection (HEF, Hailo-8L)
LEROY_DETECTION_MODEL=all_models/yolov11s.hef
LEROY_DETECTION_LABELS=all_models/yolo11s.txt

# Classification (ONNX, CPU — HAILO8 HEFs are NOT compatible with Hailo-8L)
LEROY_CLASSIFICATION_MODEL=all_models/species_classifier_nabirds.onnx
LEROY_CLASSIFICATION_LABELS=all_models/nabirds_labels.txt
```

Or pass via CLI: `python leroy.py --detection-model ... --detection-labels ...`

```bash
# Web Server Configuration
LEROY_WEB_PORT=80             # Port (default: 80)
LEROY_WEB_HOST=localhost     # Host (default: localhost)

# Browser Auto-Launch
LEROY_AUTO_LAUNCH_BROWSER=true  # Enable/disable (default: true)

# Camera Resolution Configuration
LEROY_DETECTION_WIDTH=1280   # Detection resolution width (default: 1280)
LEROY_DETECTION_HEIGHT=960   # Detection resolution height (default: 960)
LEROY_PHOTO_WIDTH=4056       # Photo resolution width (default: 4056)
LEROY_PHOTO_HEIGHT=3040      # Photo resolution height (default: 3040)
```

**Security Note**: Served over plain HTTP on port 80. HTTPS on port 443 (with a certificate) is planned long-term for encrypted remote access.

#### Manual Run (Testing)

For testing or debugging:

```bash
# Activate virtual environment
source venv/bin/activate

# Run detection script
python3 leroy.py

# Or with custom model/labels
python3 leroy.py --detection-model all_models/yolov11s.hef --detection-labels all_models/yolo11s.txt
```

**Model paths**: Configured explicitly via `leroy.env` (see Configuration above). The project uses:
- Detection: `all_models/yolov11s.hef` + `all_models/yolo11s.txt`
- Classification: `all_models/species_classifier_nabirds.onnx` + `all_models/nabirds_labels.txt`

## Architecture

- **Detection**: Configurable resolution (default: 1280x960), resized to 500px for inference
- **Photos**: Configurable high-resolution (default: 4056x3040) captured when birds are detected
- **Classification**: Runs every 30 minutes via `/etc/cron.d/leroy-classify` (root). During classification, `leroy.service` is briefly stopped and restarted by `classify.sh` — a few seconds of detection are missed per run, by design.
- **Storage**: UUID-based filenames with JSON metadata for full scientific visitation schema support
- **Camera Resolution**: Configurable via `leroy.env` (LEROY_DETECTION_WIDTH/HEIGHT, LEROY_PHOTO_WIDTH/HEIGHT)

## Web Interface

The web interface is a lightweight vanilla JavaScript app (no build step required).

**On Raspberry Pi**: Nginx runs directly on the host (installed by `install-pi5.sh`). Access at `http://your-pi-ip/`.

**Local Development**: Use Docker for preview:
```bash
make web-preview
# Or: docker-compose -f docker-compose.nginx.yml up
```

The web interface displays visitations with multi-species support, scientific names, and photo galleries. It auto-refreshes every 60 seconds.

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

The system automatically collects non-bird detections (cats, dogs — the only non-bird COCO classes) into `storage/active_learning/non_birds/` when they exceed `LEROY_NON_BIRD_THRESHOLD`. These false positives can be used to fine-tune the detection model over time.

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
   - **Models missing**: Download models from Hailo Model Explorer (see Installation section)
   - **Virtual environment missing**: Re-run `./install-pi5.sh`
   - **Driver version mismatch (error 76)**: See "Hailo Driver Version Mismatch" below

### Hailo Driver Version Mismatch (Error 76)

If you see `HAILO_INVALID_DRIVER_VERSION(76)` or "Driver version is different from library version":

**Recommended Fix (Automated):**
```bash
sudo ./fix_hailo_version.sh
```
This script will:
- Detect the version mismatch
- Remove all Hailo packages completely
- Remove kernel modules
- Reinstall hailo-all
- Prompt for reboot

**Manual Fix:**
```bash
# Remove all Hailo packages
sudo apt-get remove --purge -y hailo-all hailort hailo-platform-python3

# Remove kernel modules
sudo find /lib/modules/ -name "hailo*.ko*" -delete
sudo depmod -a

# Update and reinstall
sudo apt-get update
sudo apt-get install -y hailo-all

# REBOOT (required!)
sudo reboot

# After reboot, verify
sudo hailortcli fw-control identify
# Should NOT show version mismatch
```

**Or run the install script again:**
```bash
./install-pi5.sh
# It will detect and fix the version mismatch automatically
```

**Why this happens:** After system updates, the Hailo driver and library can get out of sync. The driver loads at boot, so a reboot is required after reinstalling. The kernel modules must be removed for a clean reinstall.

**Repository Unavailable (404 Error):**

If you see `404 Not Found` when updating packages, the Hailo repository may be:
- Temporarily unavailable
- Not supporting your OS version (trixie/sid)
- Repository URL has changed

**If packages were removed but repository unavailable:**

1. **Check if packages are in Raspberry Pi's repository:**
   ```bash
   apt-cache search hailo
   ```

2. **Check official Raspberry Pi AI Kit guide** for latest repository info:
   https://www.raspberrypi.com/documentation/accessories/ai-kit.html

3. **Once repository is available, restore packages:**
   ```bash
   sudo ./deploy/restore_hailo_from_repo.sh
   ```

4. **Or manually:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y hailo-all
   sudo reboot
   ```

**Note:** If you're on Debian 13 (trixie), the Hailo repository may not support it yet. You may need to:
- Wait for Hailo to add support
- Use a different OS version (bookworm/bullseye)
- Check Hailo Developer Zone for alternative installation methods

### Service Keeps Restarting

Check logs to identify the crash cause:
```bash
sudo journalctl -u leroy.service -f
```

Common causes:
- Camera initialization failure
- Hailo model loading error
- Missing dependencies
- Driver version mismatch (see above)

### Camera Diagnostics

**Quick Diagnostic Script:**
```bash
./diagnose_camera.sh
```

This script checks:
- Camera interface status
- Device detection (`/dev/video0`)
- Camera permissions
- picamera2 access
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

5. **Test with picamera2 (What Project Leroy uses):**
   ```bash
   # Quick diagnostic script
   ./diagnose_camera.sh
   
   # Or manual test with picamera2
   python3 << 'EOF'
   from picamera2 import Picamera2
   picam2 = Picamera2()
   picam2.configure(picam2.create_preview_configuration(main={"format": "RGB888", "size": (1280, 960)}))
   picam2.start()
   frame = picam2.capture_array()
   if frame is not None:
       print(f"Camera working! Frame: {frame.shape[1]}x{frame.shape[0]}")
   else:
       print("Camera opened but can't read frames")
   picam2.stop()
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
- **Web interface**: Visit `http://your-pi-ip/`

### Check Classification Status

Classification runs automatically every 30 minutes via `/etc/cron.d/leroy-classify` (runs as root). Each run stops/starts `leroy.service` to safely move files between `storage/detected/` and `/var/www/html/classified/`.

**View cron configuration and recent output:**
```bash
cat /etc/cron.d/leroy-classify
tail -n 30 /var/log/leroy-classify.log
```

**Use the project's Makefile shortcuts:**
```bash
make cron_status       # Show cron file, log, active user crontabs
make cron_logs         # Tail cron output + syslog CRON lines
make logrotate_status  # Show logrotate config + dry-run
```

**Run classification manually (for testing):**
```bash
sudo /home/leroy/Projects/project-leroy/classify.sh
```

## Future Enhancements

- **iNaturalist Integration**: Planned feature to submit visitations to iNaturalist. Data format is already compatible - one observation per species per visitation.

## Quick Reference

### Common Commands

```bash
# Verify models (detection HEF + classification ONNX in all_models/)
./download_models.sh

# Start service
sudo systemctl start leroy.service

# View logs
sudo journalctl -u leroy.service -f

# Test manually
source venv/bin/activate
python3 leroy.py

# Check camera
./diagnose_camera.sh

# View classification cron status
cat /etc/cron.d/leroy-classify
tail -n 30 /var/log/leroy-classify.log
```

## Additional Resources

- **Hailo Model Explorer**: https://hailo.ai/products/hailo-software/model-explorer-vision/
- **Raspberry Pi AI Kit Docs**: https://www.raspberrypi.com/documentation/accessories/ai-kit.html
