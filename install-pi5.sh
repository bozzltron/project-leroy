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

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.11+ and virtual environment
echo "Installing Python 3.11+ and virtual environment..."
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

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
    libatlas-base-dev \
    libjasper-dev \
    libqtgui4 \
    libqt4-test \
    libhdf5-dev \
    libhdf5-serial-dev \
    libhdf5-103 \
    libqtgui4 \
    libqtwebkit4 \
    libqt4-test \
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
    libcanberra-gtk-module \
    libcanberra-gtk3-module \
    python3-opencv \
    nginx \
    postfix

# Install Raspberry Pi AI Kit dependencies
echo "Installing Raspberry Pi AI Kit dependencies..."
echo "Note: Follow official Raspberry Pi AI Kit installation guide first:"
echo "https://www.raspberrypi.com/documentation/accessories/ai-kit.html"

# Check if AI Kit is installed
if [ ! -d "/opt/hailo" ] && [ ! -f "/usr/lib/libhailort.so" ]; then
    echo "Warning: Hailo AI Kit drivers not detected."
    echo "Please install the AI Kit following the official guide:"
    echo "https://www.raspberrypi.com/documentation/accessories/ai-kit.html#installing-the-ai-kit"
    read -p "Continue with installation anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Setup Python virtual environment
echo "Setting up Python virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists, removing old one..."
    rm -rf venv
fi
python3.11 -m venv venv
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
echo "Installing Hailo Python SDK..."
# Try to add Hailo repository if not already added
if [ ! -f "/etc/apt/sources.list.d/hailo.list" ]; then
    echo "Adding Hailo repository..."
    echo "deb https://packages.hailo.ai/debian bookworm main" | sudo tee /etc/apt/sources.list.d/hailo.list > /dev/null
    curl -s https://packages.hailo.ai/debian/hailo.gpg | sudo apt-key add - 2>/dev/null || {
        echo "Warning: Failed to add Hailo GPG key"
        echo "You may need to add it manually following official guide"
    }
    sudo apt-get update
fi

# Try to install Hailo SDK
if sudo apt-get install -y hailo-platform-python3 hailo-dataflow-compiler 2>/dev/null; then
    echo "Hailo SDK installed successfully"
else
    echo "Warning: Hailo SDK installation failed via apt"
    echo "This may be normal if:"
    echo "  1. Official repositories are not yet available"
    echo "  2. AI Kit drivers need to be installed first"
    echo "Please install Hailo SDK manually following official guide:"
    echo "https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
    read -p "Continue with installation? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create storage directories
echo "Creating storage directories..."
mkdir -p storage/detected
mkdir -p storage/classified
mkdir -p storage/results
mkdir -p all_models

# Create web directory structure
echo "Setting up web directory structure..."
sudo mkdir -p /var/www/html/classified
sudo chown -R $USER:www-data /var/www/html/classified
sudo chmod -R 775 /var/www/html/classified

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

# Build web interface
if [ -d "web" ]; then
    echo "Building web interface..."
    cd web
    if [ -f "package.json" ]; then
        npm install
        npm run build
        sudo cp -a build/. /var/www/html/
    fi
    cd ..
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


