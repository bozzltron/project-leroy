#!/bin/bash
# Project Leroy - Classification Script
# Called by /etc/cron.d/leroy-classify (root, every 30 min).
# Model/labels from leroy.env (LEROY_CLASSIFICATION_MODEL, LEROY_CLASSIFICATION_LABELS).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

[ -f "venv/bin/activate" ] && source venv/bin/activate || { echo "ERROR: venv not found"; exit 1; }
[ -f "leroy.env" ] && source leroy.env

if [ -z "$LEROY_CLASSIFICATION_MODEL" ] || [ -z "$LEROY_CLASSIFICATION_LABELS" ]; then
    echo "ERROR: LEROY_CLASSIFICATION_MODEL and LEROY_CLASSIFICATION_LABELS must be set in leroy.env"
    exit 1
fi

systemctl stop leroy.service
sleep 1

# Process newly detected photos (moves to /var/www/html/classified)
python3 classify.py --dir=storage/detected \
    --classification-model "$LEROY_CLASSIFICATION_MODEL" \
    --classification-labels "$LEROY_CLASSIFICATION_LABELS"

# Reclassify any already-classified photos that may be missing classifications
python3 classify.py --dir=/var/www/html/classified \
    --classification-model "$LEROY_CLASSIFICATION_MODEL" \
    --classification-labels "$LEROY_CLASSIFICATION_LABELS"

sleep 1

DATE=$(date +'%Y-%m-%d')
python3 visitation.py --dir=/var/www/html/classified --date=${DATE}

systemctl start leroy.service