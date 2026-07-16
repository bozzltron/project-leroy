#!/bin/bash
# Project Leroy - Service Run Script
# Called by systemd. Model/labels from leroy.env or hard-coded below.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"
[ ! -f "$VENV_PYTHON" ] && echo "ERROR: venv not found. Run: ./install-pi5.sh" && exit 1
! "$VENV_PYTHON" -c "from hailo_platform import VDevice" 2>/dev/null && echo "ERROR: Hailo SDK not accessible. Run: ./install-pi5.sh" && exit 1

[ -f "leroy.env" ] && source leroy.env
DET_MODEL="${LEROY_DETECTION_MODEL:-all_models/yolov11s.hef}"
DET_LABELS="${LEROY_DETECTION_LABELS:-all_models/yolo11s.txt}"

[ "${LEROY_AUTO_LAUNCH_BROWSER:-true}" = "true" ] && [ -f "launch_browser.sh" ] && bash launch_browser.sh &

exec "$VENV_PYTHON" leroy.py --detection-model "$DET_MODEL" --detection-labels "$DET_LABELS"
