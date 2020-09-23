#!/bin/bash
git pull origin master
#pip3 install -r requirements.txt
make set_resolution
./leroy.py
#python3 two_models.py
#docker run --privileged --device /dev/video0 -v `pwd`/storage:/usr/src/app/storage -p 5005:5005 -v /dev/bus/usb:/dev/bus/usb michaelbosworth/project-leroy:latest two_models.py
#docker run michaelbosworth/project-leroy:latest two_models.py