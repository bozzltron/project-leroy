# Project Leroy 

Leroy is a AI birdwatcher built from Google Coral and Raspberry Pi.  

## Set up your device
1. Setup a virtual environment
2. Install requirements

## Run detection and classification

```
python3 leroy.py
```

By default, this uses the ```mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite``` model.

You can change the model and the labels file using flags ```--model``` and ```--labels```.
