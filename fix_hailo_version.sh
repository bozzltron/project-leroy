#!/bin/bash
# Fix Hailo Driver Version Mismatch
# This script aggressively fixes driver/library version mismatches
# Based on Hailo Community recommendations for error 76 (INVALID_DRIVER_VERSION)
#
# IMPORTANT: The version mismatch IS a hard blocker - the device cannot initialize
# until driver and library versions match. This is NOT a warning that can be ignored.
#
# This script performs thorough cleanup per Hailo community best practices:
# - Removes all Hailo packages
# - Cleans up directories (/opt/hailo, /usr/local/hailo, etc.)
# - Unloads and removes kernel modules
# - Reinstalls hailo-all to sync versions
# - Requires reboot for driver to load

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

# Step 2: Remove all Hailo packages (thorough cleanup)
echo ""
echo "2. Removing all Hailo packages..."
apt-get remove --purge -y \
    hailo-all \
    hailort \
    hailo-platform-python3 \
    hailort-pcie-driver \
    2>/dev/null || true

# Remove any other hailo packages
apt-get remove --purge -y $(dpkg -l | grep hailo | awk '{print $2}') 2>/dev/null || true

# Clean up package cache
apt-get autoremove -y 2>/dev/null || true

echo "   ✓ Packages removed"

# Step 3: Clean up Hailo directories (per Hailo community recommendations)
echo ""
echo "3. Cleaning up Hailo directories..."
rm -rf /opt/hailo \
       /usr/local/hailo \
       /usr/share/hailo \
       ~/.hailo \
       /lib/firmware/hailo \
       /etc/hailo* \
       2>/dev/null || true
echo "   ✓ Directories cleaned"

# Step 4: Remove kernel modules and driver (per Hailo community recommendations)
echo ""
echo "4. Removing Hailo kernel modules and driver..."
# Try to unload the module first
rmmod hailo_pci 2>/dev/null || true

# Remove kernel modules
find /lib/modules/ -name "hailo*.ko*" -delete 2>/dev/null || true
rm -rf /lib/modules/$(uname -r)/kernel/drivers/misc/hailo_pci.ko* 2>/dev/null || true

# Update module dependencies
depmod -a 2>/dev/null || true

echo "   ✓ Kernel modules removed"

# Step 5: Fix repository configuration (if needed)
echo ""
echo "5. Checking Hailo repository configuration..."
HAILO_REPO_FILE="/etc/apt/sources.list.d/hailo.list"
if [ -f "$HAILO_REPO_FILE" ]; then
    # Detect OS version
    DETECTED_VERSION=$(lsb_release -cs 2>/dev/null || echo "bookworm")
    
    # Hailo repository doesn't support trixie/sid, use bookworm
    if [ "$DETECTED_VERSION" = "trixie" ] || [ "$DETECTED_VERSION" = "sid" ]; then
        echo "   Detected OS: $DETECTED_VERSION (not supported by Hailo repo)"
        echo "   Updating repository to use 'bookworm' instead..."
        
        # Update repository file to use bookworm
        HAILO_REPO_URL="https://hailo.ai/debian"
        if grep -q "signed-by" "$HAILO_REPO_FILE"; then
            echo "deb [signed-by=/usr/share/keyrings/hailo-archive-keyring.gpg] $HAILO_REPO_URL bookworm main" | tee "$HAILO_REPO_FILE" > /dev/null
        else
            echo "deb $HAILO_REPO_URL bookworm main" | tee "$HAILO_REPO_FILE" > /dev/null
        fi
        echo "   ✓ Repository updated to use 'bookworm'"
    else
        echo "   ✓ Repository configuration looks correct"
    fi
else
    echo "   ⚠ Hailo repository not configured"
    echo "   Will be configured during reinstall"
fi

# Step 6: Update package list
echo ""
echo "6. Updating package list..."
if apt-get update 2>&1 | grep -q "404\|Not Found"; then
    echo "   ⚠ Repository returned 404 - repository may be unavailable"
    echo "   Checking if packages are already installed locally..."
    
    # Check if packages are installed
    if dpkg -l | grep -q hailo; then
        echo "   ✓ Hailo packages are installed locally"
        echo ""
        echo "   Since repository is unavailable, we'll work with installed packages."
        echo "   The version mismatch may require manual intervention or waiting for"
        echo "   repository to become available."
        echo ""
        echo "   Options:"
        echo "   1. Wait and try again later (repository may be temporarily down)"
        echo "   2. Check official Raspberry Pi AI Kit guide for alternative installation"
        echo "   3. Contact Hailo support if issue persists"
        echo ""
        read -p "Continue with cleanup anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted. Repository unavailable."
            exit 1
        fi
        # Skip reinstall if repository unavailable
        SKIP_REINSTALL=true
    else
        echo "   ✗ Hailo packages not installed and repository unavailable"
        echo "   Cannot proceed without repository access"
        exit 1
    fi
else
    SKIP_REINSTALL=false
fi

# Step 7: Reinstall hailo-all (if repository is available)
if [ "$SKIP_REINSTALL" != "true" ]; then
    echo ""
    echo "7. Reinstalling hailo-all..."
    if apt-get install -y hailo-all; then
        echo "   ✓ hailo-all installed"
    else
        echo "   ✗ Failed to install hailo-all"
        echo ""
        echo "Troubleshooting:"
        echo "  1. Check repository is configured: cat /etc/apt/sources.list.d/hailo.list"
        echo "  2. Check network connectivity"
        echo "  3. Repository may be temporarily unavailable - try again later"
        echo "  4. Check official Raspberry Pi AI Kit installation guide:"
        echo "     https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
        exit 1
    fi
else
    echo ""
    echo "7. Skipping reinstall (repository unavailable)"
    echo "   Packages remain installed - reboot may still help"
fi

# Step 8: Verify installation
echo ""
echo "8. Verifying installation..."
if [ "$SKIP_REINSTALL" != "true" ]; then
    sleep 2  # Give system a moment to register new packages
fi

if command -v hailortcli &> /dev/null; then
    echo "   Testing: hailortcli fw-control identify"
    IDENTIFY_OUTPUT=$(hailortcli fw-control identify 2>&1 || true)
    
    if echo "$IDENTIFY_OUTPUT" | grep -q "Driver version.*is different from library version"; then
        echo "   ⚠ Version mismatch still present"
        if [ "$SKIP_REINSTALL" = "true" ]; then
            echo "   Repository was unavailable - could not reinstall packages"
            echo "   Try again later when repository is available, or:"
            echo "   1. Check official Raspberry Pi AI Kit guide"
            echo "   2. Contact Hailo support"
        else
            echo "   This may require a reboot to load the new driver"
        fi
    elif echo "$IDENTIFY_OUTPUT" | grep -q "error\|ERROR"; then
        echo "   ⚠ Error detected (may need reboot):"
        echo "$IDENTIFY_OUTPUT" | head -5
    else
        echo "   ✓ Device identified successfully!"
        echo "$IDENTIFY_OUTPUT" | head -10
    fi
else
    echo "   ⚠ hailortcli not found"
fi

# Step 9: Reboot prompt
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

