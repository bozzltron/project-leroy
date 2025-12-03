#!/bin/bash
# Project Leroy - Service Run Script
# This script is called by systemd service

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "ERROR: Virtual environment not found at venv/bin/activate"
    echo "Please run install-pi5.sh to set up the environment"
    exit 1
fi

# Update code from git repository
echo "Updating code from git repository..."
if git pull origin master; then
    echo "Code updated successfully"
else
    echo "Warning: git pull failed (repository may not be initialized or network issue)"
    # Continue anyway - service should still work with existing code
fi

# Deploy web interface
if [ -d "web/build" ]; then
    echo "Deploying web interface..."
    sudo cp -a web/build/. /var/www/html/
else
    echo "Warning: web/build directory not found, skipping web deployment"
fi

# Small delay to ensure everything is ready
sleep 1

# Run detection service
echo "Starting detection service..."
python3 leroy.py
#python3 two_models.py
#docker run --privileged --device /dev/video0 -v `pwd`/storage:/usr/src/app/storage -p 5005:5005 -v /dev/bus/usb:/dev/bus/usb michaelbosworth/project-leroy:latest two_models.py
#docker run michaelbosworth/project-leroy:latest two_models.py