#!/bin/bash
# Restore Hailo packages when repository becomes available
# Run this after repository is fixed/available

set -e

if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo"
    exit 1
fi

echo "=========================================="
echo "Restore Hailo Packages"
echo "=========================================="
echo ""

# Check repository
echo "1. Checking Hailo repository..."
if [ -f "/etc/apt/sources.list.d/hailo.list" ]; then
    echo "   Repository file exists:"
    cat /etc/apt/sources.list.d/hailo.list
else
    echo "   ⚠ Repository not configured"
    echo "   Run install-pi5.sh to configure repository"
    exit 1
fi

# Update package list
echo ""
echo "2. Updating package list..."
if apt-get update 2>&1 | grep -q "404\|Not Found"; then
    echo "   ✗ Repository still returning 404"
    echo "   Repository may be down or URL incorrect"
    echo "   Check: https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
    exit 1
fi

# Install hailo-all
echo ""
echo "3. Installing hailo-all..."
if apt-get install -y hailo-all; then
    echo "   ✓ hailo-all installed"
else
    echo "   ✗ Failed to install hailo-all"
    exit 1
fi

# Verify
echo ""
echo "4. Verifying installation..."
if command -v hailortcli &> /dev/null; then
    echo "   Testing: hailortcli fw-control identify"
    if sudo hailortcli fw-control identify 2>&1 | grep -q "Driver version.*is different"; then
        echo "   ⚠ Version mismatch still present - reboot required"
    else
        echo "   ✓ Installation verified"
    fi
fi

echo ""
echo "=========================================="
echo "REBOOT REQUIRED"
echo "=========================================="
echo "Reboot to load the new driver: sudo reboot"
