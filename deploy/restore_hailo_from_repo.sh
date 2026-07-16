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

# Install dkms first (required for Hailo kernel modules)
echo ""
echo "3. Installing dkms (required for Hailo kernel modules)..."
if apt-get install -y dkms; then
    echo "   ✓ dkms installed"
else
    echo "   ⚠ Failed to install dkms (may cause issues)"
fi

# Install hailo-all
echo ""
echo "4. Installing hailo-all..."
if apt-get install -y hailo-all; then
    echo "   ✓ hailo-all installed"
else
    echo "   ✗ Failed to install hailo-all"
    exit 1
fi

# Verify (per official documentation)
echo ""
echo "5. Verifying installation..."
if command -v hailortcli &> /dev/null; then
    echo "   Running: sudo hailortcli fw-control identify"
    IDENTIFY_OUTPUT=$(sudo hailortcli fw-control identify 2>&1 || true)
    if echo "$IDENTIFY_OUTPUT" | grep -q "Driver version.*is different"; then
        echo "   ⚠ Version mismatch still present - reboot required"
    elif [ -n "$IDENTIFY_OUTPUT" ]; then
        echo "   ✓ Installation verified"
        echo "$IDENTIFY_OUTPUT" | head -5  # Show first few lines
    else
        echo "   ⚠ Could not verify (may need reboot)"
    fi
else
    echo "   ⚠ hailortcli not found"
fi

echo ""
echo "=========================================="
echo "REBOOT REQUIRED"
echo "=========================================="
echo "Reboot to load the new driver: sudo reboot"
