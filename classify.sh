#!/bin/bash
# Project Leroy - Classification Script
# This script is called by cron job

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

sudo systemctl stop leroy.service
sleep 1
python3 classify.py --dir=storage/detected
sleep 1
#if aws --profile project-leroy s3 cp storage s3://birds91149-dev --recursive  --acl bucket-owner-full-control --exclude "detected/*" ; then
    #rm -rf storage/detected
    #rm -rf storage/classified
    #rm -rf storage/video
#fi

DATE=$(date +'%Y-%m-%d')
sudo python3 visitation.py --dir=/var/www/html/classified --date=${DATE}

sudo systemctl start leroy.service