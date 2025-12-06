#!/bin/bash
# Fix Hailo Driver Version Mismatch
# This script aggressively fixes driver/library version mismatches

set -e

echo "=========================================="
echo "Hailo Driver Version Mismatch Fix"
echo "=========================================="
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo"
    echo "Usage: sudo ./fix_hailo_version.sh"
    exit 1
fi

# Step 1: Check current status
echo "1. Checking current Hailo installation..."
if command -v hailortcli &> /dev/null; then
    echo "   Running: hailortcli fw-control identify"
    IDENTIFY_OUTPUT=$(hailortcli fw-control identify 2>&1 || true)
    
    if echo "$IDENTIFY_OUTPUT" | grep -q "Driver version.*is different from library version"; then
        echo "   ✗ Version mismatch detected"
        # Extract versions
        DRIVER_VER=$(echo "$IDENTIFY_OUTPUT" | grep -oP 'Driver version \K[0-9.]+' || echo "unknown")
        LIB_VER=$(echo "$IDENTIFY_OUTPUT" | grep -oP 'library version \K[0-9.]+' || echo "unknown")
        echo "   Driver version: $DRIVER_VER"
        echo "   Library version: $LIB_VER"
    else
        echo "   ✓ No version mismatch detected"
        echo "   If you're still seeing errors, try rebooting"
        exit 0
    fi
else
    echo "   ⚠ hailortcli not found - cannot check current status"
fi

# Step 2: Remove all Hailo packages
echo ""
echo "2. Removing all Hailo packages..."
apt-get remove --purge -y \
    hailo-all \
    hailort \
    hailo-platform-python3 \
    hailort-pcie-driver \
    2>/dev/null || true

# Also try removing any other hailo packages
apt-get remove --purge -y $(dpkg -l | grep hailo | awk '{print $2}') 2>/dev/null || true

echo "   ✓ Packages removed"

# Step 3: Remove kernel modules (if any)
echo ""
echo "3. Removing Hailo kernel modules..."
find /lib/modules/ -name "hailo*.ko*" -delete 2>/dev/null || true
depmod -a 2>/dev/null || true
echo "   ✓ Kernel modules removed"

# Step 4: Update package list
echo ""
echo "4. Updating package list..."
apt-get update

# Step 5: Reinstall hailo-all
echo ""
echo "5. Reinstalling hailo-all..."
if apt-get install -y hailo-all; then
    echo "   ✓ hailo-all installed"
else
    echo "   ✗ Failed to install hailo-all"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check repository is configured: cat /etc/apt/sources.list.d/hailo.list"
    echo "  2. Check network connectivity"
    echo "  3. Try: sudo apt-get update && sudo apt-get install -y hailo-all"
    exit 1
fi

# Step 6: Verify installation
echo ""
echo "6. Verifying installation..."
sleep 2  # Give system a moment to register new packages

if command -v hailortcli &> /dev/null; then
    echo "   Testing: hailortcli fw-control identify"
    IDENTIFY_OUTPUT=$(hailortcli fw-control identify 2>&1 || true)
    
    if echo "$IDENTIFY_OUTPUT" | grep -q "Driver version.*is different from library version"; then
        echo "   ⚠ Version mismatch still present"
        echo "   This may require a reboot to load the new driver"
    elif echo "$IDENTIFY_OUTPUT" | grep -q "error\|ERROR"; then
        echo "   ⚠ Error detected (may need reboot):"
        echo "$IDENTIFY_OUTPUT" | head -5
    else
        echo "   ✓ Device identified successfully!"
        echo "$IDENTIFY_OUTPUT" | head -10
    fi
else
    echo "   ⚠ hailortcli not found after installation"
fi

# Step 7: Reboot prompt
echo ""
echo "=========================================="
echo "REBOOT REQUIRED"
echo "=========================================="
echo ""
echo "The Hailo driver loads at boot time."
echo "A reboot is REQUIRED for the new driver version to load."
echo ""
echo "After reboot, verify with:"
echo "  sudo hailortcli fw-control identify"
echo ""
read -p "Reboot now? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Rebooting in 5 seconds..."
    sleep 5
    reboot
else
    echo ""
    echo "Please reboot manually:"
    echo "  sudo reboot"
fi

