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
   - Recommended: **YOLOv11s**, **YOLOv10s**, **YOLOv8s**, or **YOLOv8m** (best balance of speed/accuracy)
   - Alternative: **YOLOv5s** or **SSD MobileNet v2**
   - Download the **COMPILED HEF** file (not pretrained)
   - **Verify**: Model description should mention "Hailo-8L" or "hailo8l"
   - Save as: `yolov11s.hef`, `yolov10s.hef`, `yolov8s.hef`, `yolov5s.hef`, or `detection_model.hef`
   - The code will automatically detect any of these names
   - **⚠️ If you get "HEF_NOT_COMPATIBLE" error**: The model was compiled for wrong device - delete it and download Hailo-8L version

3. **Download Classification Model** (REQUIRED):
   - **CRITICAL**: Filter by AI Processor = **Hailo-8L** (NOT Hailo-8 or Hailo-10)
   - Task = **Classification**
   - Recommended: **MobileNet v3** or **MobileNet v2**
   - Note: Standard models are ImageNet-trained (~59 bird species)
   - For 964 bird species, you'll need a custom fine-tuned model
   - Download the **COMPILED HEF** file
   - **Verify**: Model description should mention "Hailo-8L" or "hailo8l"
   - Save as: `mobilenet_v3.hef` or `mobilenet_v2_1.0_224_inat_bird.hef`
   - The code will automatically detect either name
   - **⚠️ If you get "HEF_NOT_COMPATIBLE" error**: The model was compiled for wrong device - delete it and download Hailo-8L version

4. **Copy Models to Project**:
   ```bash
   # Copy downloaded HEF files to all_models/ directory
   # Detection model (use the actual filename you downloaded):
   cp ~/Downloads/yolov11s.hef all_models/
   # Or: cp ~/Downloads/yolov10s.hef all_models/
   # Or: cp ~/Downloads/yolov8s.hef all_models/
   
   # Classification model (use the actual filename you downloaded):
   cp ~/Downloads/mobilenet_v3.hef all_models/
   # Or: cp ~/Downloads/mobilenet_v2.hef all_models/mobilenet_v2_1.0_224_inat_bird.hef
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
✓ Detection model found: yolov11s.hef (5242880 bytes)
✓ Classification model found: mobilenet_v3.hef (3145728 bytes)
✓ COCO labels: coco_labels.txt
✓ Bird labels: inat_bird_labels.txt
```

**Model Requirements**:
- **Detection**: COCO-compatible model (detects 80 classes including 'bird') - **REQUIRED**
  - Supported models: YOLOv11s, YOLOv10s, YOLOv8s, YOLOv8m, YOLOv5s, SSD MobileNet v2
  - Must be compiled for Hailo-8L (download COMPILED HEF, not pretrained)
- **Classification**: Classification model (ImageNet or custom bird model) - **REQUIRED**
  - Supported models: MobileNet v3, MobileNet v2
  - Must be compiled for Hailo-8L (download COMPILED HEF, not pretrained)
  - **Note**: Standard models are ImageNet-trained with ~59 bird species. For 964 bird species, you'll need a custom fine-tuned model or use the ImageNet model as a base.

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
python3 leroy.py --model all_models/yolov11s.hef --labels all_models/coco_labels.txt
# Or: python3 leroy.py --model all_models/yolov8s.hef --labels all_models/coco_labels.txt
```

**Default Model Detection**: Automatically detects and uses any of these detection models (in priority order):
- `detection_model.hef` (generic name)
- `yolov11s.hef` (YOLOv11 small - latest)
- `yolov10s.hef` (YOLOv10 small)
- `yolov8s.hef` (YOLOv8 small)
- `yolov5s.hef` (YOLOv5 small - backward compatibility)
- `ssd_mobilenet_v2_coco.hef` (SSD MobileNet v2 - fallback)

**Default Classification Model**: Automatically detects and uses any of these classification models (in priority order):
- `mobilenet_v3.hef` (MobileNet v3 - recommended)
- `mobilenet_v2_1.0_224_inat_bird.hef` (MobileNet v2 with iNaturalist naming)
- `mobilenet_v2.hef` (MobileNet v2 - generic)

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

The system automatically collects low-confidence bird classifications for review in `storage/active_learning/`. These can be used for future model fine-tuning.

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
   sudo ./restore_hailo_from_repo.sh
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

## Quick Reference

### Supported Model Names

**Detection Models** (automatically detected):
- `detection_model.hef` (generic)
- `yolov11s.hef` (YOLOv11 small - latest, recommended)
- `yolov10s.hef` (YOLOv10 small)
- `yolov8s.hef` (YOLOv8 small)
- `yolov8m.hef` (YOLOv8 medium)
- `yolov5s.hef` (YOLOv5 small)
- `ssd_mobilenet_v2_coco.hef` (SSD MobileNet v2)

**Classification Models** (automatically detected):
- `mobilenet_v3.hef` (MobileNet v3 - recommended)
- `mobilenet_v2_1.0_224_inat_bird.hef` (MobileNet v2 with iNaturalist naming)
- `mobilenet_v2.hef` (MobileNet v2 - generic)

### Common Commands

```bash
# Verify models
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
```

## Additional Resources

- **Architecture**: `.cursor/rules/architecture.mdc` - Detailed system architecture
- **Hailo Model Explorer**: https://hailo.ai/products/hailo-software/model-explorer-vision/
- **Raspberry Pi AI Kit Docs**: https://www.raspberrypi.com/documentation/accessories/ai-kit.html
