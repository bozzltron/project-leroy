#!/bin/bash
#python3 -m venv .
#pip3 install https://dl.google.com/coral/python/tflite_runtime-2.1.0.post1-cp37-cp37m-linux_armv7l.whl
#pip3 install opencv-python 
pip3 install opencv-contrib-python image imutils psutil
sudo cp service/leroy.service /lib/systemd/system/leroy.service
sudo chmod 644 /lib/systemd/system/leroy.service
sudo systemctl daemon-reload
sudo systemctl enable leroy.service
cd all_models
wget https://github.com/google-coral/edgetpu/raw/master/test_data/mobilenet_v2_1.0_224_inat_bird_quant_edgetpu.tflite
wget https://github.com/google-coral/edgetpu/raw/master/test_data/inat_bird_labels.txt
wget https://github.com/google-coral/edgetpu/raw/master/test_data/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite
wget https://dl.google.com/coral/canned_models/coco_labels.txt