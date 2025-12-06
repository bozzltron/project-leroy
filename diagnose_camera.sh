#!/bin/bash
# Camera Diagnostic Script for Project Leroy
# Tests camera connectivity and functionality

echo "=========================================="
echo "Project Leroy - Camera Diagnostics"
echo "=========================================="
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠ Warning: This script is designed for Raspberry Pi"
    echo ""
fi

# 1. Check camera interface is enabled
echo "1. Checking Camera Interface Status..."
if [ -f "/boot/firmware/config.txt" ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
elif [ -f "/boot/config.txt" ]; then
    CONFIG_FILE="/boot/config.txt"
else
    CONFIG_FILE=""
fi

if [ -n "$CONFIG_FILE" ] && [ -f "$CONFIG_FILE" ]; then
    if grep -q "^start_x=1" "$CONFIG_FILE" 2>/dev/null; then
        echo "   ✓ Camera interface enabled in $CONFIG_FILE"
    else
        echo "   ✗ Camera interface NOT enabled in $CONFIG_FILE"
        echo "     Run: sudo raspi-config → Interface Options → Camera → Enable"
        echo "     Or add to $CONFIG_FILE: start_x=1"
    fi
else
    echo "   ⚠ Could not find config.txt"
fi

# 2. Check for camera devices
echo ""
echo "2. Checking for Camera Devices..."
if [ -d "/dev/video0" ] || [ -c "/dev/video0" ]; then
    echo "   ✓ /dev/video0 found"
    ls -l /dev/video* 2>/dev/null | head -5
else
    echo "   ✗ /dev/video0 not found"
    echo "     Camera may not be connected or detected"
fi

# 3. Check v4l2 tools (if available)
echo ""
echo "3. Checking v4l2-utils..."
if command -v v4l2-ctl &> /dev/null; then
    echo "   ✓ v4l2-ctl available"
    echo ""
    echo "   Camera Information:"
    v4l2-ctl --device=/dev/video0 --all 2>/dev/null | head -20 || echo "   ⚠ Could not query /dev/video0"
else
    echo "   ⚠ v4l2-utils not installed"
    echo "     Install: sudo apt-get install v4l-utils"
fi

# 4. Check rpicam tools (Raspberry Pi official)
echo ""
echo "4. Checking rpicam tools..."
if command -v rpicam-hello &> /dev/null; then
    echo "   ✓ rpicam-hello available"
    echo ""
    echo "   Testing camera with rpicam-hello (2 second preview)..."
    timeout 2 rpicam-hello 2>&1 | head -10 || echo "   ⚠ rpicam-hello failed"
elif command -v raspistill &> /dev/null; then
    echo "   ✓ raspistill available (legacy)"
    echo "   Note: Using legacy camera tools"
else
    echo "   ⚠ rpicam tools not found"
    echo "     Install: sudo apt-get install rpicam-apps"
fi

# 5. Test with OpenCV (Python)
echo ""
echo "5. Testing Camera with OpenCV (Python)..."
python3 << 'EOF'
import sys
import cv2

print("   Testing OpenCV camera access...")
try:
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        print("   ✓ Camera opened successfully")
        
        # Try to read a frame
        ret, frame = cap.read()
        if ret and frame is not None:
            height, width = frame.shape[:2]
            print(f"   ✓ Frame captured: {width}x{height}")
            
            # Get camera properties
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            print(f"   ✓ Camera properties: {actual_width}x{actual_height} @ {fps} fps")
        else:
            print("   ✗ Could not read frame from camera")
        
        cap.release()
    else:
        print("   ✗ Failed to open camera")
        print("   Check:")
        print("     - Camera is connected")
        print("     - Camera interface is enabled")
        print("     - User is in 'video' group: groups")
        print("     - Permissions: ls -l /dev/video0")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)
EOF

OPENCV_EXIT=$?
if [ $OPENCV_EXIT -eq 0 ]; then
    echo "   ✓ OpenCV test passed"
else
    echo "   ✗ OpenCV test failed"
fi

# 6. Check user permissions
echo ""
echo "6. Checking User Permissions..."
if groups | grep -q video; then
    echo "   ✓ User is in 'video' group"
else
    echo "   ✗ User is NOT in 'video' group"
    echo "     Fix: sudo usermod -aG video $USER"
    echo "     Then logout and login again"
fi

# 7. Check camera device permissions
echo ""
echo "7. Checking Camera Device Permissions..."
if [ -c "/dev/video0" ]; then
    PERMS=$(ls -l /dev/video0 | awk '{print $1, $3, $4}')
    echo "   Device: $PERMS"
    if ls -l /dev/video0 | grep -q "video\|crw"; then
        echo "   ✓ Device permissions look correct"
    else
        echo "   ⚠ Check device permissions"
    fi
fi

# 8. Test with Project Leroy's camera manager
echo ""
echo "8. Testing with Project Leroy Camera Manager..."
if [ -f "camera_manager.py" ]; then
    python3 << 'EOF'
import sys
sys.path.insert(0, '.')
try:
    from camera_manager import CameraManager
    print("   Testing camera manager initialization...")
    camera = CameraManager(camera_idx=0)
    if camera.initialize():
        print("   ✓ Camera manager initialized successfully")
        res = camera.get_detection_resolution()
        print(f"   ✓ Detection resolution: {res[0]}x{res[1]}")
        res = camera.get_photo_resolution()
        print(f"   ✓ Photo resolution: {res[0]}x{res[1]}")
        camera.release()
    else:
        print("   ✗ Camera manager failed to initialize")
        sys.exit(1)
except ImportError as e:
    print(f"   ⚠ Could not import camera_manager: {e}")
    print("   (This is OK if dependencies aren't installed)")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)
EOF
    CAMERA_MGR_EXIT=$?
    if [ $CAMERA_MGR_EXIT -eq 0 ]; then
        echo "   ✓ Camera manager test passed"
    else
        echo "   ✗ Camera manager test failed"
    fi
else
    echo "   ⚠ camera_manager.py not found (run from project directory)"
fi

# Summary
echo ""
echo "=========================================="
echo "Diagnostic Summary"
echo "=========================================="
echo ""
echo "If camera tests failed, try:"
echo "  1. Enable camera interface: sudo raspi-config"
echo "  2. Add user to video group: sudo usermod -aG video $USER"
echo "  3. Reboot: sudo reboot"
echo "  4. Check camera connection (cable, power)"
echo ""
echo "For more help, see README.md troubleshooting section"
echo ""

