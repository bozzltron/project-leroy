#!/bin/bash
# Project Leroy Installation Script for Raspberry Pi 5 + AI Kit
# This script installs all dependencies and sets up the system for Pi 5 with Hailo AI Kit

set -e  # Exit on error

echo "=========================================="
echo "Project Leroy - Raspberry Pi 5 + AI Kit"
echo "Installation Script"
echo "=========================================="

# Check if running on Raspberry Pi 5
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi 5"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Enable required interfaces
echo "=========================================="
echo "Enabling Required Interfaces"
echo "=========================================="
echo ""

# Enable Camera interface (required for HQ Camera)
echo "Enabling Camera interface..."
if command -v raspi-config &> /dev/null; then
    if raspi-config nonint get_camera | grep -q "1"; then
        echo "Enabling camera interface via raspi-config..."
        raspi-config nonint do_camera 0
        echo "✓ Camera interface enabled (reboot may be required)"
    else
        echo "✓ Camera interface already enabled"
    fi
else
    # Fallback: enable via config.txt
    CONFIG_FILE="/boot/firmware/config.txt"
    if [ ! -f "$CONFIG_FILE" ]; then
        CONFIG_FILE="/boot/config.txt"
    fi
    if [ -f "$CONFIG_FILE" ]; then
        if ! grep -q "^start_x=1" "$CONFIG_FILE" 2>/dev/null; then
            echo "Enabling camera interface in $CONFIG_FILE..."
            if ! grep -q "^start_x" "$CONFIG_FILE" 2>/dev/null; then
                echo "start_x=1" | sudo tee -a "$CONFIG_FILE" > /dev/null
            else
                sudo sed -i 's/^start_x=.*/start_x=1/' "$CONFIG_FILE"
            fi
            echo "gpu_mem=128" | sudo tee -a "$CONFIG_FILE" > /dev/null
            echo "✓ Camera interface enabled in config.txt (reboot required)"
        else
            echo "✓ Camera interface already enabled in config.txt"
        fi
    fi
fi

# Enable SSH (required for remote access)
echo ""
echo "Enabling SSH..."
if command -v raspi-config &> /dev/null; then
    if raspi-config nonint get_ssh | grep -q "1"; then
        echo "Enabling SSH via raspi-config..."
        raspi-config nonint do_ssh 0
        echo "✓ SSH enabled"
    else
        echo "✓ SSH already enabled"
    fi
else
    # Fallback: enable via systemd
    if ! systemctl is-enabled ssh > /dev/null 2>&1; then
        sudo systemctl enable ssh
        sudo systemctl start ssh
        echo "✓ SSH enabled via systemd"
    else
        echo "✓ SSH already enabled"
    fi
fi

# Summary of enabled interfaces
echo ""
echo "Interface Status:"
echo "  ✓ Camera interface: Enabled (required for HQ Camera)"
echo "  ✓ SSH: Enabled (required for remote access)"
echo "  ✓ PCIe: Will be configured below (required for AI Kit)"
echo ""

# Update system and firmware (required for AI Kit)
echo "Updating system packages and firmware..."
sudo apt-get update
sudo apt-get full-upgrade -y

# Update EEPROM firmware (required for AI Kit PCIe support)
echo "Updating Raspberry Pi EEPROM firmware..."
if command -v rpi-eeprom-update &> /dev/null; then
    sudo rpi-eeprom-update -a || echo "Note: EEPROM update may require reboot"
else
    echo "Note: rpi-eeprom-update not available (may need to install rpi-eeprom-update)"
fi

# Detect Python 3 version
echo "Detecting Python 3 version..."
PYTHON3_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
PYTHON3_MAJOR=$(echo $PYTHON3_VERSION | cut -d. -f1)
PYTHON3_MINOR=$(echo $PYTHON3_VERSION | cut -d. -f2)

echo "Found Python $PYTHON3_VERSION"

# Check if Python 3.9 or higher
if [ "$PYTHON3_MAJOR" -lt 3 ] || ([ "$PYTHON3_MAJOR" -eq 3 ] && [ "$PYTHON3_MINOR" -lt 9 ]); then
    echo "ERROR: Python 3.9+ is required, found Python $PYTHON3_VERSION"
    echo "Attempting to install Python 3.11..."
    sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
    if command -v python3.11 &> /dev/null; then
        PYTHON3_CMD=python3.11
        PYTHON3_VERSION="3.11"
        echo "Python 3.11 installed successfully"
    else
        echo "ERROR: Could not install Python 3.11"
        echo "Please install Python 3.9+ manually and run this script again"
        exit 1
    fi
else
    PYTHON3_CMD=python3
    echo "Using system Python $PYTHON3_VERSION"
fi

# Install Python 3 and virtual environment support
echo "Installing Python $PYTHON3_VERSION and virtual environment..."
if [ "$PYTHON3_VERSION" = "3.11" ]; then
    sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
else
    # For other versions, install generic python3 packages
    sudo apt-get install -y python3 python3-venv python3-dev python3-pip
fi

# Note: HQ Camera configuration
echo "Note: This installation assumes Raspberry Pi HQ Camera is connected"
echo "Camera will be accessed via OpenCV VideoCapture (index 0)"

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    curl \
    wget \
    libhdf5-dev \
    libhdf5-serial-dev \
    python3-pyqt5 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libgtk-3-dev \
    libcanberra-gtk3-module \
    python3-opencv \
    nginx \
    postfix

# Install Chromium browser (package name varies by OS version)
echo "Installing Chromium browser..."
if sudo apt-get install -y chromium-browser 2>/dev/null; then
    echo "✓ chromium-browser installed"
elif sudo apt-get install -y chromium 2>/dev/null; then
    echo "✓ chromium installed (creating symlink for compatibility)"
    # Create symlink if chromium is installed but script expects chromium-browser
    if [ ! -f /usr/bin/chromium-browser ] && [ -f /usr/bin/chromium ]; then
        sudo ln -s /usr/bin/chromium /usr/bin/chromium-browser
    fi
else
    echo "⚠ Could not install Chromium browser"
    echo "  You may need to install it manually or use a different browser"
fi

# Note: Removed obsolete packages that are no longer available:
# - libatlas-base-dev (replaced by OpenBLAS, not needed for OpenCV)
# - libjasper-dev (JPEG2000 support, optional)
# - libqtgui4, libqt4-test, libqtwebkit4 (Qt4 packages, obsolete)
# - libhdf5-103 (replaced by newer libhdf5 packages)
# - libcanberra-gtk-module (replaced by libcanberra-gtk3-module)

# Install Raspberry Pi AI Kit
echo "=========================================="
echo "Raspberry Pi AI Kit Installation"
echo "=========================================="

# Remove any incorrect repository entries first
if [ -f "/etc/apt/sources.list.d/hailo.list" ]; then
    echo "Removing existing Hailo repository configuration..."
    sudo rm -f /etc/apt/sources.list.d/hailo.list
    echo "Repository file removed"
fi

# Check if Hailo SDK is already installed
HAILO_INSTALLED=false
if python3 -c "from hailo_platform import Device" 2>/dev/null; then
    echo "✓ Hailo SDK Python package is already installed"
    HAILO_INSTALLED=true
elif command -v hailortcli &> /dev/null; then
    echo "✓ Hailo tools detected (hailortcli found)"
    HAILO_INSTALLED=true
elif [ -f "/opt/hailo/bin/hailortcli" ] || [ -f "/usr/lib/libhailort.so" ]; then
    echo "✓ Hailo drivers detected"
    HAILO_INSTALLED=true
fi

if [ "$HAILO_INSTALLED" = false ]; then
    echo "Installing Raspberry Pi AI Kit..."
    echo ""
    echo "This will install:"
    echo "  - Hailo AI Kit drivers and SDK"
    echo "  - Python bindings (hailo-platform-python3)"
    echo ""
    
    # Configure Hailo repository
    echo "Configuring Hailo repository..."
    
    # Detect OS version (bookworm, bullseye, etc.)
    DETECTED_VERSION=$(lsb_release -cs 2>/dev/null || echo "bookworm")
    echo "Detected OS version: $DETECTED_VERSION"
    
    # Hailo repository typically supports bookworm (Raspberry Pi OS based on Debian 12)
    # For newer versions (trixie, etc.), use bookworm as fallback
    if [ "$DETECTED_VERSION" = "trixie" ] || [ "$DETECTED_VERSION" = "sid" ]; then
        echo "Note: Hailo repository may not support $DETECTED_VERSION, using 'bookworm' instead"
        OS_VERSION="bookworm"
    else
        OS_VERSION="$DETECTED_VERSION"
    fi
    
    # Try the official Hailo repository URL
    HAILO_REPO_URL="https://hailo.ai/debian"
    echo "Adding Hailo repository: $HAILO_REPO_URL (using $OS_VERSION)"
    
    # Add repository
    echo "deb $HAILO_REPO_URL $OS_VERSION main" | sudo tee /etc/apt/sources.list.d/hailo.list > /dev/null
    
    # Try to add GPG key (may not be required, but try common locations)
    echo "Adding GPG key..."
    if curl -fsSL "$HAILO_REPO_URL/gpg" 2>/dev/null | sudo apt-key add - 2>/dev/null; then
        echo "✓ GPG key added"
    elif curl -fsSL "$HAILO_REPO_URL/hailo.gpg" 2>/dev/null | sudo apt-key add - 2>/dev/null; then
        echo "✓ GPG key added (alternate location)"
    else
        echo "⚠ Could not add GPG key automatically"
        echo "  You may need to add it manually or the repository may use signed-by"
        # Try using signed-by method (more modern)
        sudo rm -f /etc/apt/sources.list.d/hailo.list
        echo "deb [signed-by=/usr/share/keyrings/hailo-archive-keyring.gpg] $HAILO_REPO_URL $OS_VERSION main" | sudo tee /etc/apt/sources.list.d/hailo.list > /dev/null
        # Try to download and install keyring
        if curl -fsSL "$HAILO_REPO_URL/gpg" -o /tmp/hailo.gpg 2>/dev/null; then
            sudo gpg --dearmor < /tmp/hailo.gpg | sudo tee /usr/share/keyrings/hailo-archive-keyring.gpg > /dev/null
            rm -f /tmp/hailo.gpg
            echo "✓ GPG keyring installed"
        fi
    fi
    
    # Update package list
    echo "Updating package list..."
    if sudo apt-get update 2>&1 | grep -q "hailo"; then
        echo "✓ Hailo repository found in package list"
    else
        echo "⚠ Hailo repository may not be accessible"
        echo "  This could be due to:"
        echo "  - Network connectivity issues"
        echo "  - Incorrect repository URL"
        echo "  - Repository requires authentication"
    fi
    
    # Try to install hailo-all (includes everything)
    echo ""
    echo "Installing hailo-all package..."
    if sudo apt-get install -y hailo-all; then
        echo "✓ Hailo AI Kit installed successfully"
        HAILO_INSTALLED=true
    else
        echo "⚠ Failed to install hailo-all"
        echo ""
        echo "Trying alternative: installing individual packages..."
        if sudo apt-get install -y hailo-platform-python3 2>/dev/null; then
            echo "✓ hailo-platform-python3 installed"
            HAILO_INSTALLED=true
        else
            echo "⚠ Could not install Hailo packages"
            echo ""
            echo "Please check:"
            echo "  1. Network connectivity"
            echo "  2. Repository URL: $HAILO_REPO_URL"
            echo "  3. Official Raspberry Pi AI Kit guide:"
            echo "     https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
            echo ""
            read -p "Continue with rest of installation? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Installation cancelled. Please install AI Kit first."
                exit 1
            fi
        fi
    fi
fi

# Enable PCIe Gen 3.0 for optimal performance (if not already enabled)
echo ""
echo "Configuring PCIe for AI Kit..."
PCIE_REBOOT_NEEDED=false

# Check if PCIe Gen 3.0 is already enabled in config.txt
if [ -f "/boot/firmware/config.txt" ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
elif [ -f "/boot/config.txt" ]; then
    CONFIG_FILE="/boot/config.txt"
else
    CONFIG_FILE=""
fi

if [ -n "$CONFIG_FILE" ]; then
    # Check if dtparam=pcie_gen3 is already set
    if grep -q "^dtparam=pcie_gen3=1" "$CONFIG_FILE" 2>/dev/null; then
        echo "✓ PCIe Gen 3.0 is already enabled in $CONFIG_FILE"
    elif grep -q "^dtparam=pcie_gen3=0" "$CONFIG_FILE" 2>/dev/null; then
        echo "PCIe Gen 3.0 is disabled, enabling..."
        sudo sed -i 's/^dtparam=pcie_gen3=0/dtparam=pcie_gen3=1/' "$CONFIG_FILE"
        echo "✓ PCIe Gen 3.0 enabled in $CONFIG_FILE"
        PCIE_REBOOT_NEEDED=true
    elif ! grep -q "dtparam=pcie_gen3" "$CONFIG_FILE" 2>/dev/null; then
        echo "Adding PCIe Gen 3.0 configuration..."
        echo "dtparam=pcie_gen3=1" | sudo tee -a "$CONFIG_FILE" > /dev/null
        echo "✓ PCIe Gen 3.0 enabled in $CONFIG_FILE"
        PCIE_REBOOT_NEEDED=true
    fi
    
    # Also check for dtoverlay (alternative method)
    if ! grep -q "dtoverlay=pcie-gen3" "$CONFIG_FILE" 2>/dev/null && ! grep -q "dtparam=pcie_gen3" "$CONFIG_FILE" 2>/dev/null; then
        # If neither method is present, add dtparam (preferred)
        if [ "$PCIE_REBOOT_NEEDED" = false ]; then
            echo "dtparam=pcie_gen3=1" | sudo tee -a "$CONFIG_FILE" > /dev/null
            echo "✓ PCIe Gen 3.0 enabled in $CONFIG_FILE"
            PCIE_REBOOT_NEEDED=true
        fi
    fi
else
    echo "⚠ Could not find config.txt file"
    echo "  PCIe configuration may need to be done manually"
fi

# Try raspi-config as fallback (if available and supports it)
if [ "$PCIE_REBOOT_NEEDED" = false ] && command -v raspi-config &> /dev/null; then
    # Check if raspi-config supports PCIe speed option
    if raspi-config nonint get_pcie_speed &>/dev/null; then
        PCIE_SPEED=$(raspi-config nonint get_pcie_speed 2>/dev/null || echo "unknown")
        if [ "$PCIE_SPEED" != "1" ]; then
            if raspi-config nonint do_pcie_speed 1 &>/dev/null; then
                echo "✓ PCIe Gen 3.0 enabled via raspi-config"
                PCIE_REBOOT_NEEDED=true
            fi
        else
            echo "✓ PCIe Gen 3.0 is already enabled (via raspi-config)"
        fi
    fi
fi

# Ensure Hailo packages are in sync (bulletproof approach)
# Always reinstall to prevent driver/library version mismatches
echo ""
echo "Ensuring Hailo packages are in sync..."
if [ "$HAILO_INSTALLED" = true ] || command -v hailortcli &> /dev/null; then
    echo "Checking for driver/library version mismatch..."
    
    # Check current versions
    IDENTIFY_OUTPUT=$(sudo hailortcli fw-control identify 2>&1 || true)
    if echo "$IDENTIFY_OUTPUT" | grep -q "Driver version.*is different from library version"; then
        echo "⚠ Driver version mismatch detected - fixing..."
        echo ""
        echo "Removing all Hailo packages for clean reinstall..."
        sudo apt-get remove --purge -y hailo-all hailort hailo-platform-python3 2>/dev/null || true
        
        echo "Updating package list..."
        sudo apt-get update
        
        echo "Reinstalling hailo-all..."
        if sudo apt-get install -y hailo-all; then
            echo "✓ hailo-all reinstalled"
            echo ""
            echo "⚠ REBOOT REQUIRED to load new driver"
            echo "After reboot, verify with: sudo hailortcli fw-control identify"
            echo ""
            read -p "Reboot now? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "Rebooting in 5 seconds..."
                sleep 5
                sudo reboot
                exit 0
            else
                echo "Please reboot manually before using the service"
            fi
        else
            echo "⚠ Failed to reinstall hailo-all"
            echo "You may need to manually fix the version mismatch"
        fi
    else
        echo "✓ No version mismatch detected (or device not accessible yet)"
        echo "Reinstalling hailo-all to ensure everything is up to date..."
        sudo apt-get update
        sudo apt-get install --reinstall -y hailo-all || {
            echo "⚠ Failed to reinstall hailo-all, but continuing..."
        }
    fi
fi

# Verify AI Kit installation
echo ""
echo "Verifying AI Kit installation..."
if command -v hailortcli &> /dev/null; then
    echo "Running hailortcli fw-control identify..."
    if sudo hailortcli fw-control identify 2>/dev/null; then
        echo "✓ AI Kit hardware detected and working"
    else
        echo "⚠ AI Kit hardware not detected (may need reboot)"
        echo "This is normal if PCIe was just configured - reboot required"
        PCIE_REBOOT_NEEDED=true
    fi
else
    echo "⚠ hailortcli not found (AI Kit may not be fully installed)"
fi

# Check and enable HailoRT service (needed for multi-process inference)
echo ""
echo "Checking HailoRT service..."
if systemctl list-unit-files | grep -q "hailort.service"; then
    if ! systemctl is-active --quiet hailort.service; then
        echo "Starting HailoRT service..."
        sudo systemctl enable hailort.service
        sudo systemctl start hailort.service
        if systemctl is-active --quiet hailort.service; then
            echo "✓ HailoRT service started"
        else
            echo "⚠ HailoRT service failed to start (may not be needed for single-process)"
        fi
    else
        echo "✓ HailoRT service is already running"
    fi
else
    echo "Note: HailoRT service not found (may not be installed or needed)"
fi

# Warn about reboot if needed
if [ "$PCIE_REBOOT_NEEDED" = true ]; then
    echo ""
    echo "=========================================="
    echo "REBOOT REQUIRED"
    echo "=========================================="
    echo "A reboot is required for PCIe changes to take effect."
    echo "After reboot, you can:"
    echo "  1. Verify AI Kit: sudo hailortcli fw-control identify"
    echo "  2. Continue with: ./install-pi5.sh (will skip already-installed parts)"
    echo ""
    read -p "Reboot now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Rebooting in 5 seconds..."
        sleep 5
        sudo reboot
        exit 0
    else
        echo "Please reboot manually before using the AI Kit"
    fi
fi

# Setup Python virtual environment
echo "Setting up Python virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists, removing old one..."
    rm -rf venv
fi
# Use --system-site-packages to access system-installed packages (like Hailo SDK)
$PYTHON3_CMD -m venv --system-site-packages venv
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo "Installing Python dependencies..."
pip install \
    numpy \
    pillow \
    opencv-contrib-python \
    psutil \
    imutils

# Optional: Install Bluesky posting support
echo "Installing optional Bluesky posting support..."
pip install atproto || echo "Note: Bluesky posting not available (install atproto manually if needed)"

# Install Hailo Python SDK
echo "=========================================="
echo "Hailo SDK Installation"
echo "=========================================="
echo "IMPORTANT: The Hailo SDK must be installed following the official Raspberry Pi guide:"
echo "https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
echo ""
echo "The AI Kit installation includes:"
echo "  1. Hardware drivers"
echo "  2. Hailo SDK packages"
echo "  3. Repository configuration"
echo ""

# Remove any incorrect repository entries
if [ -f "/etc/apt/sources.list.d/hailo.list" ]; then
    echo "Removing existing Hailo repository configuration..."
    sudo rm -f /etc/apt/sources.list.d/hailo.list
    echo "Repository file removed"
fi

# Check if Hailo SDK is already installed
if python3 -c "from hailo_platform import Device" 2>/dev/null; then
    echo "✓ Hailo SDK is already installed"
elif [ -f "/opt/hailo/bin/hailortcli" ] || [ -f "/usr/lib/libhailort.so" ]; then
    echo "✓ Hailo drivers detected, but Python SDK may need to be installed"
    echo "  Try: sudo apt-get install -y hailo-platform-python3"
else
    echo "⚠ Hailo SDK not detected"
    echo ""
    echo "Please install the AI Kit following the official guide:"
    echo "https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
    echo ""
    echo "After installing the AI Kit, verify with:"
    echo "  python3 -c 'from hailo_platform import Device; print(\"Hailo SDK installed\")'"
    echo ""
    read -p "Continue with rest of installation? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled. Please install AI Kit first."
        exit 1
    fi
fi

# Create storage directories
echo "Creating storage directories..."
mkdir -p storage/detected
mkdir -p storage/classified
mkdir -p storage/results
mkdir -p storage/active_learning
mkdir -p all_models

# Note: Subdirectories are created automatically:
# - storage/detected/{date}/{visitation_id}/ - Created by photo.py when saving
# - /var/www/html/classified/{date}/{visitation_id}/ - Created by classify.py when moving files
# - storage/active_learning/* - Created by active_learning.py on init

# Create environment configuration file if it doesn't exist
if [ ! -f "leroy.env" ]; then
    echo "Creating leroy.env configuration file..."
    if [ -f "leroy.env.example" ]; then
        cp leroy.env.example leroy.env
        echo "✓ Created leroy.env from example (customize as needed)"
    else
        # Create default config
        cat > leroy.env <<EOF
# Project Leroy - Environment Configuration
LEROY_WEB_PORT=8080
LEROY_WEB_HOST=localhost
LEROY_AUTO_LAUNCH_BROWSER=true
EOF
        echo "✓ Created default leroy.env"
    fi
else
    echo "leroy.env already exists, skipping creation"
fi

# Create web directory structure
echo "Setting up web directory structure..."
sudo mkdir -p /var/www/html/classified
sudo chown -R $USER:www-data /var/www/html/classified
sudo chmod -R 775 /var/www/html/classified

# Setup nginx configuration for custom port
echo "Setting up nginx..."
LEROY_WEB_PORT="${LEROY_WEB_PORT:-8080}"

# Create nginx configuration for Project Leroy
NGINX_CONF="/etc/nginx/sites-available/leroy"
if [ ! -f "$NGINX_CONF" ]; then
    echo "Creating nginx configuration for port ${LEROY_WEB_PORT}..."
    sudo tee "$NGINX_CONF" > /dev/null <<EOF
# Project Leroy - Nginx Configuration
# Custom port (${LEROY_WEB_PORT}) for security

server {
    listen ${LEROY_WEB_PORT};
    server_name localhost;
    root /var/www/html;
    index index.html;

    # Enable gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;

    # Serve static files
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Serve classified images
    location /classified/ {
        alias /var/www/html/classified/;
        autoindex off;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Serve visitations.json
    location /visitations.json {
        add_header Cache-Control "no-cache, must-revalidate";
        expires 0;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF
    
    # Enable the site
    sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/leroy
    
    # Remove default site if it exists (optional, to avoid conflicts)
    if [ -f /etc/nginx/sites-enabled/default ]; then
        echo "Disabling default nginx site..."
        sudo rm /etc/nginx/sites-enabled/default
    fi
    
    # Test nginx configuration
    if sudo nginx -t; then
        echo "✓ Nginx configuration is valid"
    else
        echo "Warning: Nginx configuration test failed"
    fi
else
    echo "Nginx configuration already exists"
fi

# Start nginx
if systemctl is-active --quiet nginx; then
    echo "Nginx is already running"
    sudo systemctl reload nginx
else
    echo "Starting nginx on port ${LEROY_WEB_PORT}..."
    sudo systemctl enable nginx
    sudo systemctl start nginx
    if systemctl is-active --quiet nginx; then
        echo "✓ Nginx started successfully on port ${LEROY_WEB_PORT}"
    else
        echo "Warning: Nginx failed to start. Check: sudo systemctl status nginx"
    fi
fi

# Check if git repository exists
echo "Checking git repository..."
if [ ! -d ".git" ]; then
    echo "Warning: Git repository not found in current directory"
    echo "The service will auto-update via 'git pull' when it starts"
    echo "Please ensure you're in the project directory and git is initialized"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "Git repository found - service will auto-update on restart"
fi

# Get current directory for service file
PROJECT_DIR="$(pwd)"
echo "Project directory: $PROJECT_DIR"

# Install systemd service (with dynamic paths)
echo "Installing systemd service..."
# Create service file with current directory
# Replace the base path (this will also update PATH environment variable)
sed "s|/home/leroy/Projects/project-leroy|$PROJECT_DIR|g" service/leroy.service > /tmp/leroy.service
sudo cp /tmp/leroy.service /etc/systemd/system/leroy.service
sudo chmod 644 /etc/systemd/system/leroy.service
sudo systemctl daemon-reload
sudo systemctl enable leroy.service
echo "Service installed with path: $PROJECT_DIR"

# Add user to necessary groups
echo "Adding user to necessary groups..."
sudo usermod -aG video $USER
sudo usermod -aG www-data $USER

# Download models
echo "=========================================="
echo "Model Installation"
echo "=========================================="

# Check if HEF models already exist
if [ "$(ls -A all_models/*.hef 2>/dev/null)" ]; then
    echo "HEF models found in all_models/"
    echo "Skipping model download"
else
    echo "HEF models not found."
    echo ""
    read -p "Download HEF models from Hailo Model Zoo now? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        if [ -f "download_models.sh" ]; then
            echo "Running download_models.sh..."
            bash download_models.sh
        else
            echo "ERROR: download_models.sh not found"
            echo "Please download models manually from Hailo Model Zoo:"
            echo "https://github.com/hailo-ai/hailo_model_zoo/tree/v2.15/hailo_models"
        fi
    else
        echo "Skipping model download. You can download models later with:"
        echo "  ./download_models.sh"
    fi
fi

# Setup cron job for classification (if not exists)
echo "Setting up cron job for classification..."
CRON_SCRIPT="$(pwd)/classify.sh"
CRON_JOB="0 * * * * $CRON_SCRIPT"  # Run every hour

if ! crontab -l 2>/dev/null | grep -q "$CRON_SCRIPT"; then
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Cron job added: $CRON_JOB"
else
    echo "Cron job already exists"
fi

# Deploy web interface (lightweight vanilla JS - no build needed)
if [ -d "web" ]; then
    echo "Deploying web interface..."
    if [ -f "web/index.html" ]; then
        sudo cp web/index.html web/styles.css web/app.js /var/www/html/
        echo "Web interface deployed (lightweight vanilla JS version)"
    else
        echo "Warning: web/index.html not found"
    fi
fi

# Verify installation
echo ""
echo "Verifying installation..."
VERIFY_FAILED=0

if [ ! -f "venv/bin/activate" ]; then
    echo "ERROR: Virtual environment not created"
    VERIFY_FAILED=1
fi

if [ ! -f "leroy.py" ]; then
    echo "ERROR: leroy.py not found"
    VERIFY_FAILED=1
fi

if [ ! -f "run.sh" ]; then
    echo "ERROR: run.sh not found"
    VERIFY_FAILED=1
fi

if ! systemctl is-enabled leroy.service > /dev/null 2>&1; then
    echo "WARNING: Service not enabled (this may be normal if installation failed earlier)"
fi

if [ $VERIFY_FAILED -eq 0 ]; then
    echo "Installation verification: PASSED"
else
    echo "Installation verification: FAILED"
    echo "Please check errors above"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Service Configuration:"
echo "  - Project directory: $PROJECT_DIR"
echo "  - Service will auto-update via 'git pull' on each start"
echo "  - Virtual environment: venv/"
echo ""
echo "Next steps:"
echo "1. Ensure Raspberry Pi AI Kit is properly installed and configured"
echo "2. Convert your models to HEF format using Hailo Dataflow Compiler"
echo "3. Place HEF models in all_models/ directory"
echo "4. Test the system: sudo systemctl start leroy.service"
echo "5. Check logs: sudo journalctl -u leroy.service -f"
echo "6. Check status: sudo systemctl status leroy.service"
echo ""
echo "For AI Kit installation guide:"
echo "https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
echo ""
echo "Note: The service will automatically pull latest code from git"
echo "      when it starts (via run.sh)"
echo ""


