#!/bin/bash
sudo systemctl stop leroy.service
python3 classify.py --dir=storage/detected
sudo systemctl start leroy.service
