#!/bin/bash
# Project Leroy - Service Run Script
# This script is called by systemd service

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    
    # Verify we're using the venv Python
    if [ -z "$VIRTUAL_ENV" ]; then
        echo "ERROR: Virtual environment not activated properly"
        exit 1
    fi
    echo "Using virtual environment: $VIRTUAL_ENV"
    echo "Python path: $(which python3)"
    
    # Check if venv has system-site-packages enabled
    if [ -f "$VIRTUAL_ENV/pyvenv.cfg" ]; then
        if grep -q "include-system-site-packages = true" "$VIRTUAL_ENV/pyvenv.cfg"; then
            echo "✓ Virtual environment has system-site-packages enabled"
        else
            echo "⚠ WARNING: Virtual environment does NOT have system-site-packages enabled"
            echo "  This means system-installed packages (like Hailo SDK) won't be accessible"
            echo "  To fix, recreate the venv:"
            echo "    rm -rf venv"
            echo "    python3 -m venv --system-site-packages venv"
            echo "    source venv/bin/activate"
            echo "    pip install --upgrade pip setuptools wheel"
            echo "    pip install numpy pillow opencv-contrib-python psutil imutils"
        fi
    fi
    
    # Verify Hailo SDK is accessible in this environment
    if ! python3 -c "from hailo_platform import Device" 2>/dev/null; then
        echo "ERROR: Hailo SDK not accessible in virtual environment"
        echo ""
        echo "Troubleshooting:"
        echo "  1. Check if Hailo SDK is installed system-wide:"
        echo "     python3 -c 'from hailo_platform import Device; print(\"OK\")'"
        echo ""
        echo "  2. If system-wide works but venv doesn't, recreate venv with system-site-packages:"
        echo "     rm -rf venv"
        echo "     python3 -m venv --system-site-packages venv"
        echo "     source venv/bin/activate"
        echo "     pip install --upgrade pip setuptools wheel"
        echo "     pip install numpy pillow opencv-contrib-python psutil imutils"
        echo ""
        echo "  3. Restart service after recreating venv:"
        echo "     sudo systemctl restart leroy.service"
        echo ""
        exit 1
    else
        echo "✓ Hailo SDK is accessible in virtual environment"
    fi
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
# Use explicit path to venv Python - this is the recommended approach for systemd
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Virtual environment Python not found at $VENV_PYTHON"
    exit 1
fi

echo "Starting detection service..."
echo "Using Python: $VENV_PYTHON"
echo "Python version: $($VENV_PYTHON --version)"

# Verify Hailo SDK one more time with explicit Python path
if ! "$VENV_PYTHON" -c "from hailo_platform import Device" 2>/dev/null; then
    echo "ERROR: Hailo SDK not accessible with $VENV_PYTHON"
    echo "This Python should have access to system packages via --system-site-packages"
    exit 1
fi

# Execute Python directly (don't use exec, let systemd manage the process)
exec "$VENV_PYTHON" leroy.py