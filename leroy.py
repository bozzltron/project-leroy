#!/usr/bin/env python3
import argparse
import collections
import common
import cv2
import os
import sys
import numpy as np
import re
import time
import logging
import psutil
import uuid
import imutils
import tflite_runtime.interpreter as tflite
from PIL import Image
from edgetpu.utils import dataset_utils
from random import randint
from imutils.video import FPS
from imutils.video import VideoStream
from visitations import Visitations

print("cv version" + cv2.__version__)

Object = collections.namedtuple('Object', ['id', 'score', 'bbox'])

def load_labels(path):
    p = re.compile(r'\s*(\d+)(.+)')
    with open(path, 'r', encoding='utf-8') as f:
       lines = (p.match(line).groups() for line in f.readlines())
       return {int(num): text.strip() for num, text in lines}

class BBox(collections.namedtuple('BBox', ['xmin', 'ymin', 'xmax', 'ymax'])):
    """Bounding box.
    Represents a rectangle which sides are either vertical or horizontal, parallel
    to the x or y axis.
    """
    __slots__ = ()

def get_output(interpreter, score_threshold, top_k, image_scale=1.0):
    """Returns list of detected objects."""
    boxes = common.output_tensor(interpreter, 0)
    class_ids = common.output_tensor(interpreter, 1)
    scores = common.output_tensor(interpreter, 2)
    count = int(common.output_tensor(interpreter, 3))

    def make(i):
        ymin, xmin, ymax, xmax = boxes[i]
        return Object(
            id=int(class_ids[i]),
            score=scores[i],
            bbox=BBox(xmin=np.maximum(0.0, xmin),
                      ymin=np.maximum(0.0, ymin),
                      xmax=np.minimum(1.0, xmax),
                      ymax=np.minimum(1.0, ymax)))

    return [make(i) for i in range(top_k) if scores[i] >= score_threshold]

def main():

    try:
        default_model_dir = 'all_models'
        default_model = 'ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite'
        default_labels = 'coco_labels.txt'
        parser = argparse.ArgumentParser()
        parser.add_argument('--model', help='.tflite model path',
                            default=os.path.join(default_model_dir,default_model))
        parser.add_argument('--labels', help='label file path',
                            default=os.path.join(default_model_dir, default_labels))
        parser.add_argument('--top_k', type=int, default=3,
                            help='number of categories with highest score to display')
        parser.add_argument('--camera_idx', type=int, help='Index of which video source to use. ', default = 0)
        parser.add_argument('--threshold', type=float, default=0.1,
                            help='classifier score threshold')
        args = parser.parse_args()

        #Initialize logging files
        logging.basicConfig(filename='storage/results.log',
                            format='%(asctime)s-%(message)s',
                            level=logging.DEBUG)

        print('Loading {} with {} labels.'.format(args.model, args.labels))
        interpreter = common.make_interpreter(args.model)
        interpreter.allocate_tensors()
        labels = load_labels(args.labels)

        
        #vs = VideoStream(src=args.camera_idx, resolution=(2048, 1536)).start()
        #cap = vs.stream
        cap = cv2.VideoCapture(args.camera_idx)
        #cap = cv2.VideoCapture('videotestsrc ! video/x-raw,framerate=20/1 ! videoscale ! videoconvert ! appsink', cv2.CAP_GSTREAMER)
        time.sleep(2.0)

        cap.set(3, 3264)
        cap.set(4, 2448)
        # 4:3 resolutions
        # 640×480, 800×600, 960×720, 1024×768, 1280×960, 1400×1050,
        # 1440×1080 , 1600×1200, 1856×1392, 1920×1440, 2048×1536
        # 5 MP
        cap.set(3, 2048)
        cap.set(4, 1536)
        
        out = None
        fps = FPS().start()
        is_stopped = False
        current_fps = 4.0

        visitations = Visitations()

        while cap.isOpened():
            try:
                
                ret, frame = cap.read()
                if not ret:
                    break

                if fps._numFrames < 500:
                    fps.update()
                else:
                    fps.stop()
                    current_fps = fps.fps()
                    logging.info("[INFO] elasped time: {:.2f}".format(fps.elapsed()))
                    logging.info("[INFO] approx. FPS: {:.2f}".format(fps.fps()))
                    fps = FPS().start()

                cv2_im = frame
                #imutils.resize(cv2_im, width=500)
                cv2_im_rgb = cv2.cvtColor(cv2_im, cv2.COLOR_BGR2RGB)
                pil_im = Image.fromarray(cv2_im)

                common.set_input(interpreter, pil_im)
                interpreter.invoke()
                objs = get_output(interpreter, score_threshold=args.threshold, top_k=args.top_k)
                height, width, channels = cv2_im.shape
                
                visitations.update(objs, cv2_im, labels)
                
                cv2.namedWindow('Leroy',cv2.WINDOW_NORMAL)
                cv2.resizeWindow('Leroy', 800, 600)
                cv2.imshow('Leroy', cv2_im)

            except KeyboardInterrupt:
                print('Interrupted')
                try:
                    sys.exit(0)
                except SystemExit:
                    os._exit(0)
            except:
                logging.exception('Failed while looping.')
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

    except: 
        logging.exception('Failed on main program.')

if __name__ == '__main__':
    main()