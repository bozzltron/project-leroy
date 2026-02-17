#!/bin/bash
# Project Leroy - Update script (git pull + web deploy)
# Run manually when you want to update code. run.sh no longer does this on every start.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Updating code..."
git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || echo "Warning: git pull failed"

if [ -f "web/index.html" ]; then
    echo "Deploying web interface..."
    sudo cp web/index.html web/styles.css web/app.js /var/www/html/
fi

echo "Update complete. Restart service: sudo systemctl restart leroy.service"
