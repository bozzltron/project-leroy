#!/usr/bin/python
import argparse
import collections
import common
import cv2
import numpy as np
import os
import sys
from PIL import Image
import re
import tflite_runtime.interpreter as tflite
import time
import logging
from edgetpu.classification.engine import ClassificationEngine
from edgetpu.utils import dataset_utils
import psutil
from random import randint
import uuid

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

def get_classification_output(interpreter, score_threshold, top_k, image_scale=1.0):
    """Returns list of detected objects."""
    scores = common.classification_output_tensor(interpreter, 0)
    
    print('scores')
    print(scores)
    
    def make(i):
        return Object(
            score=scores[i]
        )

    return [make(i) for i in range(top_k) if scores[i] >= score_threshold]

def intersects(box1, box2):
    box1x0, box1y0, box1x1, box1y1 = list(box1)
    box2x0, box2y0, box2x1, box2y1 = list(box2)
    #return not (self.top_right.x < other.bottom_left.x or self.bottom_left.x > other.top_right.x or self.top_right.y < other.bottom_left.y or self.bottom_left.y > other.top_right.y)
    return not (box1x0 < box2x1 or box1x1 > box2x0 or box1y0 < box2y1 or box1y1 > box2y0)

def main():
    default_model_dir = 'all_models'
    default_model = 'mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite'
    default_labels = 'coco_labels.txt'
    default_classification_model = 'mobilenet_v2_1.0_224_inat_bird_quant_edgetpu.tflite'
    default_classification_label = 'inat_bird_labels.txt'
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
    multiTracker = cv2.MultiTracker_create()

    #Initialize logging files
    logging.basicConfig(filename='storage/results.log',
                        format='%(asctime)s-%(message)s',
                        level=logging.DEBUG)

    print('Loading {} with {} labels.'.format(args.model, args.labels))
    interpreter = common.make_interpreter(args.model)
    interpreter.allocate_tensors()
    labels = load_labels(args.labels)

    # Prepare labels.
    classification_interpreter = common.make_interpreter(os.path.join(default_model_dir,default_classification_model))
    classification_interpreter.allocate_tensors()
    classification_labels = load_labels(os.path.join(default_model_dir,default_classification_label))

    cap = cv2.VideoCapture(args.camera_idx)
    cap.set(3, 1024)
    cap.set(4, 768)
    # 4:3 resolutions
    # 640×480, 800×600, 960×720, 1024×768, 1280×960, 1400×1050,
    # 1440×1080 , 1600×1200, 1856×1392, 1920×1440, 2048×1536
    # 5 MP
    #cap.set(3, 2048)
    #cap.set(4, 1536)
    
    bboxes = []
    colors = [] 
    visitation = []
    trackers = []

    while cap.isOpened():
        try:
            ret, frame = cap.read()
            if not ret:
                break
            
            success, boxes = multiTracker.update(frame)
            if len(boxes) > 0:
                logging.info("success {}".format(success))
                logging.info("boxes {}".format(boxes))

            cv2_im = frame
            cv2_im_rgb = cv2.cvtColor(cv2_im, cv2.COLOR_BGR2RGB)
            pil_im = Image.fromarray(cv2_im_rgb)

            common.set_input(interpreter, pil_im)
            interpreter.invoke()
            objs = get_output(interpreter, score_threshold=args.threshold, top_k=args.top_k)
            height, width, channels = cv2_im.shape
            
            bird_detected = False
            for obj in objs:
                x0, y0, x1, y1 = list(obj.bbox)
                x0, y0, x1, y1 = int(x0*width), int(y0*height), int(x1*width), int(y1*height)
                percent = int(100 * obj.score)
                object_label = labels.get(obj.id, obj.id)
                label = '{}% {}'.format(percent, object_label)
                hdd = psutil.disk_usage('/')
                
                if object_label == 'bird' and percent > 30:
                    bird_detected = True
                    new_bird = True
                    
                    for bbox in boxes:
                        if intersects(bbox, obj.bbox):
                            logging.info("intersected.. same bird")
                            new_bird = False
                    
                    if new_bird:
                        logging.info("found a new bird")
                        bboxes.append(obj.bbox)
                        colors.append((randint(64, 255), randint(64, 255), randint(64, 255)))
                        tracker = cv2.TrackerCSRT_create()
                        trackers.append(tracker)
                        multiTracker.add(tracker, cv2_im, obj.bbox)

                    if hdd.percent < 95:
                        boxed_image_path = "storage/detected/boxed_{}_{}.png".format(time.strftime("%Y-%m-%d_%H-%M-%S"), percent)
                        full_image_path = "storage/detected/full_{}_{}.png".format(time.strftime("%Y-%m-%d_%H-%M-%S"), percent)
                        cv2.imwrite( boxed_image_path, cv2_im[y0:y1,x0:x1] )
                        cv2.imwrite( full_image_path, cv2_im ) 
                    else:
                        print("Not enough disk space")

            if bird_detected == False and len(trackers) > 0:
                logging.info("clearing trackers")
                for tracker in trackers:
                    tracker.clear()
                multiTracker = cv2.MultiTracker_create()
                boxes = []
                colors = []
                trackers = []

            for i, newbox in enumerate(boxes):
                p1 = (int(newbox[0]), int(newbox[1]))
                p2 = (int(newbox[0] + newbox[2]), int(newbox[1] + newbox[3]))
                cv2_im = cv2.rectangle(cv2_im, p1, p2, colors[i], 2, 1)
            
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
            logging.exception('Something happened.')
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


def append_objs_to_img(cv2_im, objs, labels):
    height, width, channels = cv2_im.shape
    for obj in objs:
        x0, y0, x1, y1 = list(obj.bbox)
        x0, y0, x1, y1 = int(x0*width), int(y0*height), int(x1*width), int(y1*height)
        percent = int(100 * obj.score)
        object_label = labels.get(obj.id, obj.id)
        label = '{}% {}'.format(percent, object_label)

        cv2_im = cv2.rectangle(cv2_im, (x0, y0), (x1, y1), (0, 255, 0), 2)
        cv2_im = cv2.putText(cv2_im, label, (x0, y0+30),
                             cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)
    return cv2_im

if __name__ == '__main__':
    main()
