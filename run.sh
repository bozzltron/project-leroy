#!/bin/bash
git pull origin master
#pip3 install -r requirements.txt
rm run.log
python3 -m trace --trace leroy.py >> run.log
