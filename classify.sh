#!/bin/bash
# Project Leroy - Classification Script
# Called by /etc/cron.d/leroy-classify (root, every 30 min). Model/labels from leroy.env or hard-coded below.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

[ -f "venv/bin/activate" ] && source venv/bin/activate || { echo "ERROR: venv not found"; exit 1; }
[ -f "leroy.env" ] && source leroy.env
CLASS_MODEL="${LEROY_CLASSIFICATION_MODEL:-all_models/mobilenet_v3.hef}"
CLASS_LABELS="${LEROY_CLASSIFICATION_LABELS:-all_models/mobilenet_v3.txt}"

systemctl stop leroy.service
sleep 1
python3 classify.py --dir=storage/detected --classification-model "$CLASS_MODEL" --classification-labels "$CLASS_LABELS"
sleep 1

DATE=$(date +'%Y-%m-%d')
python3 visitation.py --dir=/var/www/html/classified --date=${DATE}

systemctl start leroy.service