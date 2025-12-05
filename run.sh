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
if git pull origin main; then
    echo "Code updated successfully"
else
    echo "Warning: git pull failed (repository may not be initialized or network issue)"
    # Continue anyway - service should still work with existing code
fi

# Deploy web interface (lightweight vanilla JS version)
if [ -f "web/index.html" ]; then
    echo "Deploying web interface..."
    sudo cp web/index.html web/styles.css web/app.js /var/www/html/
    echo "Web interface deployed (lightweight vanilla JS version)"
else
    echo "Warning: web/index.html not found, skipping web deployment"
fi

# Small delay to ensure everything is ready
sleep 1

# Launch browser (if enabled and not already open) - runs in background
# Load config to check if auto-launch is enabled
if [ -f "leroy.env" ]; then
    source leroy.env
fi
LEROY_AUTO_LAUNCH_BROWSER="${LEROY_AUTO_LAUNCH_BROWSER:-true}"

if [ "$LEROY_AUTO_LAUNCH_BROWSER" = "true" ] && [ -f "launch_browser.sh" ]; then
    echo "Launching browser for web interface..."
    bash launch_browser.sh &
elif [ "$LEROY_AUTO_LAUNCH_BROWSER" != "true" ]; then
    echo "Browser auto-launch is disabled (LEROY_AUTO_LAUNCH_BROWSER=false)"
fi

# Run detection service
echo "Starting detection service..."
python3 leroy.py