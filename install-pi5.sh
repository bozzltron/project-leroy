#!/bin/bash
# Project Leroy Installation Script for Raspberry Pi 5 + AI Kit

set -e

echo "Project Leroy - Installation"
echo "============================"
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    read -p "Warning: Not detected as Raspberry Pi. Continue? (y/N) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

# Enable interfaces
echo "Enabling interfaces..."
if command -v raspi-config &> /dev/null; then
    raspi-config nonint get_camera | grep -q "1" && raspi-config nonint do_camera 0
    raspi-config nonint get_ssh | grep -q "1" && raspi-config nonint do_ssh 0
else
    CONFIG_FILE="/boot/firmware/config.txt"
    [ ! -f "$CONFIG_FILE" ] && CONFIG_FILE="/boot/config.txt"
    [ -f "$CONFIG_FILE" ] && ! grep -q "^start_x=1" "$CONFIG_FILE" && \
        echo "start_x=1" | sudo tee -a "$CONFIG_FILE" > /dev/null && \
        echo "gpu_mem=128" | sudo tee -a "$CONFIG_FILE" > /dev/null
    systemctl is-enabled ssh > /dev/null 2>&1 || (sudo systemctl enable ssh && sudo systemctl start ssh)
fi

# Update system
echo "Updating system..."
sudo apt-get update -qq
sudo apt-get full-upgrade -y -qq

# Python setup
PYTHON3_CMD=python3
if ! python3 --version 2>&1 | grep -qE "3\.(9|1[0-9])"; then
    echo "Installing Python 3.11..."
    sudo apt-get install -y -qq python3.11 python3.11-venv python3.11-dev python3-pip
    PYTHON3_CMD=python3.11
fi

# Install dependencies
echo "Installing dependencies..."
sudo apt-get install -y -qq \
    build-essential cmake git curl wget \
    libhdf5-dev libhdf5-serial-dev \
    python3-opencv nginx \
    python3-pyqt5 libcanberra-gtk3-module \
    libavcodec-dev libavformat-dev libswscale-dev libv4l-dev \
    libxvidcore-dev libx264-dev libjpeg-dev libpng-dev libtiff-dev libgtk-3-dev

# Install Chromium
sudo apt-get install -y -qq chromium-browser 2>/dev/null || \
    (sudo apt-get install -y -qq chromium && \
     [ ! -f /usr/bin/chromium-browser ] && [ -f /usr/bin/chromium ] && \
     sudo ln -s /usr/bin/chromium /usr/bin/chromium-browser) || true

# Install Hailo AI Kit
echo "Installing Hailo AI Kit..."
if ! python3 -c "from hailo_platform import Device" 2>/dev/null && \
   ! command -v hailortcli &> /dev/null; then
    
    # Configure repository
    DETECTED_VERSION=$(lsb_release -cs 2>/dev/null || echo "bookworm")
    [ "$DETECTED_VERSION" = "trixie" ] || [ "$DETECTED_VERSION" = "sid" ] && OS_VERSION="bookworm" || OS_VERSION="$DETECTED_VERSION"
    
    echo "deb https://hailo.ai/debian $OS_VERSION main" | sudo tee /etc/apt/sources.list.d/hailo.list > /dev/null
    
    # Try GPG key
    curl -fsSL "https://hailo.ai/debian/gpg" 2>/dev/null | sudo apt-key add - 2>/dev/null || \
        (curl -fsSL "https://hailo.ai/debian/gpg" -o /tmp/hailo.gpg 2>/dev/null && \
         sudo gpg --dearmor < /tmp/hailo.gpg | sudo tee /usr/share/keyrings/hailo-archive-keyring.gpg > /dev/null && \
         rm -f /tmp/hailo.gpg && \
         echo "deb [signed-by=/usr/share/keyrings/hailo-archive-keyring.gpg] https://hailo.ai/debian $OS_VERSION main" | \
         sudo tee /etc/apt/sources.list.d/hailo.list > /dev/null) || true
    
    sudo apt-get update -qq
    sudo apt-get install -y -qq dkms hailo-all || {
        echo "ERROR: Failed to install Hailo AI Kit"
        echo "See: https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
        exit 1
    }
fi

# Configure PCIe
echo "Configuring PCIe..."
CONFIG_FILE="/boot/firmware/config.txt"
[ ! -f "$CONFIG_FILE" ] && CONFIG_FILE="/boot/config.txt"
PCIE_REBOOT_NEEDED=false

if [ -f "$CONFIG_FILE" ]; then
    if ! grep -q "^dtparam=pcie_gen3=1" "$CONFIG_FILE" 2>/dev/null; then
        grep -q "^dtparam=pcie_gen3=0" "$CONFIG_FILE" && \
            sudo sed -i 's/^dtparam=pcie_gen3=0/dtparam=pcie_gen3=1/' "$CONFIG_FILE" || \
            echo "dtparam=pcie_gen3=1" | sudo tee -a "$CONFIG_FILE" > /dev/null
        PCIE_REBOOT_NEEDED=true
    fi
fi

# Ensure Hailo packages are in sync
if command -v hailortcli &> /dev/null; then
    if sudo hailortcli fw-control identify 2>&1 | grep -q "Driver version.*is different"; then
        echo "Fixing Hailo version mismatch..."
        sudo apt-get remove --purge -y hailo-all hailort hailo-platform-python3 2>/dev/null || true
        sudo apt-get update -qq
        sudo apt-get install -y -qq hailo-all
        PCIE_REBOOT_NEEDED=true
    else
        sudo apt-get install --reinstall -y -qq hailo-all 2>/dev/null || true
    fi
fi

# Verify AI Kit
if command -v hailortcli &> /dev/null; then
    if ! sudo hailortcli fw-control identify 2>&1 | grep -q "Driver version.*is different"; then
        echo "✓ AI Kit verified"
    else
        PCIE_REBOOT_NEEDED=true
    fi
fi

# HailoRT service
systemctl list-unit-files | grep -q "hailort.service" && \
    ! systemctl is-active --quiet hailort.service && \
    (sudo systemctl enable hailort.service && sudo systemctl start hailort.service) || true

# Python virtual environment
echo "Setting up Python environment..."
[ -d "venv" ] && rm -rf venv
$PYTHON3_CMD -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade -q pip setuptools wheel
pip install -q numpy pillow opencv-contrib-python psutil imutils atproto || true

# Create directories
mkdir -p storage/{detected,classified,results,active_learning} all_models

# Environment config
[ ! -f "leroy.env" ] && [ -f "leroy.env.example" ] && cp leroy.env.example leroy.env || \
    [ ! -f "leroy.env" ] && cat > leroy.env <<EOF
LEROY_WEB_PORT=8080
LEROY_WEB_HOST=localhost
LEROY_AUTO_LAUNCH_BROWSER=true
EOF

# Web directory
sudo mkdir -p /var/www/html/classified
sudo chown -R $USER:www-data /var/www/html/classified
sudo chmod -R 775 /var/www/html/classified

# Nginx configuration
LEROY_WEB_PORT="${LEROY_WEB_PORT:-8080}"
NGINX_CONF="/etc/nginx/sites-available/leroy"
[ ! -f "$NGINX_CONF" ] && sudo tee "$NGINX_CONF" > /dev/null <<EOF
server {
    listen ${LEROY_WEB_PORT};
    server_name localhost;
    root /var/www/html;
    index index.html;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /classified/ {
        alias /var/www/html/classified/;
        autoindex off;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /visitations.json {
        add_header Cache-Control "no-cache, must-revalidate";
        expires 0;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/leroy
[ -f /etc/nginx/sites-enabled/default ] && sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t -q && sudo systemctl reload nginx || (sudo systemctl enable nginx && sudo systemctl start nginx)

# Systemd service
PROJECT_DIR="$(pwd)"
sed "s|/home/leroy/Projects/project-leroy|$PROJECT_DIR|g" service/leroy.service | sudo tee /etc/systemd/system/leroy.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable leroy.service

# User groups
sudo usermod -aG video,www-data $USER

# Models
echo ""
echo "Downloading models..."
VALID_MODELS=0
for hef_file in all_models/*.hef; do
    [ -f "$hef_file" ] && [ -s "$hef_file" ] && VALID_MODELS=$((VALID_MODELS + 1)) || rm -f "$hef_file"
done

if [ $VALID_MODELS -eq 0 ]; then
    read -p "Download HEF models now? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        [ -f "download_models.sh" ] && bash download_models.sh || {
            echo "ERROR: download_models.sh not found"
            exit 1
        }
    fi
fi

# Cron job
CRON_SCRIPT="$(pwd)/classify.sh"
CRON_JOB="0 * * * * $CRON_SCRIPT"
crontab -l 2>/dev/null | grep -q "$CRON_SCRIPT" || \
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

# Deploy web interface
[ -d "web" ] && [ -f "web/index.html" ] && \
    sudo cp web/index.html web/styles.css web/app.js /var/www/html/ 2>/dev/null || true

# Reboot prompt
if [ "$PCIE_REBOOT_NEEDED" = true ]; then
    echo ""
    echo "REBOOT REQUIRED for PCIe changes"
    echo "After reboot, verify: sudo hailortcli fw-control identify"
    read -p "Reboot now? (y/N) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] && (echo "Rebooting in 5 seconds..." && sleep 5 && sudo reboot) || \
        echo "Please reboot manually: sudo reboot"
fi

echo ""
echo "Installation complete!"
echo "Start service: sudo systemctl start leroy.service"
echo "View logs: sudo journalctl -u leroy.service -f"
