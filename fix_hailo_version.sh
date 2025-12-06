#!/bin/bash
# Fix Hailo Driver Version Mismatch (Error 76)

set -e

[ "$EUID" -ne 0 ] && echo "Run with sudo: sudo ./fix_hailo_version.sh" && exit 1

echo "Fixing Hailo driver version mismatch..."
echo ""

# Check current status
if command -v hailortcli &> /dev/null; then
    if ! sudo hailortcli fw-control identify 2>&1 | grep -q "Driver version.*is different"; then
        echo "✓ No version mismatch detected"
        exit 0
    fi
fi

# Remove all Hailo packages
echo "Removing Hailo packages..."
apt-get remove --purge -y hailo-all hailort hailo-platform-python3 hailort-pcie-driver 2>/dev/null || true
apt-get remove --purge -y $(dpkg -l | grep hailo | awk '{print $2}') 2>/dev/null || true
apt-get autoremove -y -qq 2>/dev/null || true

# Clean directories
echo "Cleaning directories..."
rm -rf /opt/hailo /usr/local/hailo /usr/share/hailo ~/.hailo /lib/firmware/hailo /etc/hailo* 2>/dev/null || true

# Remove kernel modules
echo "Removing kernel modules..."
rmmod hailo_pci 2>/dev/null || true
find /lib/modules/ -name "hailo*.ko*" -delete 2>/dev/null || true
depmod -a 2>/dev/null || true

# Fix repository if needed
HAILO_REPO_FILE="/etc/apt/sources.list.d/hailo.list"
if [ -f "$HAILO_REPO_FILE" ]; then
    DETECTED_VERSION=$(lsb_release -cs 2>/dev/null || echo "bookworm")
    [ "$DETECTED_VERSION" = "trixie" ] || [ "$DETECTED_VERSION" = "sid" ] && OS_VERSION="bookworm" || OS_VERSION="$DETECTED_VERSION"
    
    if grep -q "signed-by" "$HAILO_REPO_FILE"; then
        echo "deb [signed-by=/usr/share/keyrings/hailo-archive-keyring.gpg] https://hailo.ai/debian $OS_VERSION main" | tee "$HAILO_REPO_FILE" > /dev/null
    else
        echo "deb https://hailo.ai/debian $OS_VERSION main" | tee "$HAILO_REPO_FILE" > /dev/null
    fi
fi

# Update and reinstall
echo "Reinstalling Hailo packages..."
apt-get update -qq
apt-get install -y -qq dkms hailo-all || {
    echo "ERROR: Failed to reinstall hailo-all"
    echo "Check: https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
    exit 1
}

# Verify
echo ""
echo "Verifying installation..."
if command -v hailortcli &> /dev/null; then
    if sudo hailortcli fw-control identify 2>&1 | grep -q "Driver version.*is different"; then
        echo "⚠ Version mismatch still present - reboot required"
    else
        echo "✓ Installation verified"
        sudo hailortcli fw-control identify 2>&1 | head -5
    fi
fi

echo ""
echo "REBOOT REQUIRED"
echo "After reboot, verify: sudo hailortcli fw-control identify"
read -p "Reboot now? (y/N) " -n 1 -r
echo
[[ $REPLY =~ ^[Yy]$ ]] && (echo "Rebooting in 5 seconds..." && sleep 5 && reboot) || \
    echo "Reboot manually: sudo reboot"
