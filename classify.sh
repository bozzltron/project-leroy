#!/bin/bash
sudo systemctl stop leroy.service
sleep 1
python3 classify.py --dir=storage/detected
sleep 1
#rm -rf storage/detected
sudo systemctl start leroy.service
