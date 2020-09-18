#!/bin/bash

echo "setup python virtual env"
python3 -m venv .

echo "install dependencies"
pip3 install https://dl.google.com/coral/python/tflite_runtime-2.1.0.post1-cp37-cp37m-linux_armv7l.whl
sudo apt-get install libatlas-base-dev python3-opencvsudo libjasper-dev libqtgui4 libqt4-test
pip3 install image imutils psutil
pip3 install opencv-contrib-python==4.1.0.25
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update
sudo apt-get install libedgetpu1-std
sudo apt-get install python3-edgetpu

echo "install leroy service"
sudo cp service/leroy.service /lib/systemd/system/leroy.service
sudo chmod 644 /lib/systemd/system/leroy.service
sudo systemctl daemon-reload
sudo systemctl enable leroy.service
mkdir all_models

echo "download models and labels"
cd all_models
wget https://github.com/google-coral/edgetpu/raw/master/test_data/mobilenet_v2_1.0_224_inat_bird_quant_edgetpu.tflite
wget https://github.com/google-coral/edgetpu/raw/master/test_data/inat_bird_labels.txt
wget https://github.com/google-coral/edgetpu/raw/master/test_data/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite
wget https://dl.google.com/coral/canned_models/coco_labels.txt

echo "install messaging for cron"
sudo apt install postfix

echo "add user to group allowing device access"
sudo usermod -aG plugdev $USER

echo "install nginx for web"
sudo apt install nginx
sudo usermod -a -G www-data pi

echo "bad frame fix"
sudo rmmod uvcvideo
sudo modprobe uvcvideo nodrop=1 timeout=5000 quirks=0x80

sudo reboot
