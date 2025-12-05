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
    postfix \
    chromium-browser

# Note: Removed obsolete packages that are no longer available:
# - libatlas-base-dev (replaced by OpenBLAS, not needed for OpenCV)
# - libjasper-dev (JPEG2000 support, optional)
# - libqtgui4, libqt4-test, libqtwebkit4 (Qt4 packages, obsolete)
# - libhdf5-103 (replaced by newer libhdf5 packages)
# - libcanberra-gtk-module (replaced by libcanberra-gtk3-module)

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
$PYTHON3_CMD -m venv venv
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


