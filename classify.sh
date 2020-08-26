#!/bin/bash
sudo systemctl stop leroy.service
python3 classify.py --dir=storage
sudo systemctl start leroy.service
