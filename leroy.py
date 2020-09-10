#!/usr/bin/python
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
from imutils.video import WebcamVideoStream

print("cv version" + cv2.__version__)
print(cv2.getBuildInformation())

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

def intersects(box1, box2):
    logging.info("box1 {}".format(box1))
    logging.info("box2 {}".format(box2))
    box1x0, box1y0, box1x1, box1y1 = list(box1)
    box2x0, box2y0, box2x1, box2y1 = list(box2)
    return not (box1x0 < box2x1 or box1x1 > box2x0 or box1y0 < box2y1 or box1y1 > box2y0)

def disk_has_space():
    hdd = psutil.disk_usage('/')
    return hdd.percent < 95

def clarity(image):
	# compute the Laplacian of the image and then return the focus
	# measure, which is simply the variance of the Laplacian
  gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
  return 0 if image is None else cv2.Laplacian(gray, cv2.CV_64F).var()

def is_focused(image):
    return clarity(image) > 100

def main():

    try:
        default_model_dir = 'all_models'
        default_model = 'mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite'
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
        multiTracker = cv2.MultiTracker_create()

        #Initialize logging files
        logging.basicConfig(filename='storage/results.log',
                            format='%(asctime)s-%(message)s',
                            level=logging.DEBUG)

        print('Loading {} with {} labels.'.format(args.model, args.labels))
        interpreter = common.make_interpreter(args.model)
        interpreter.allocate_tensors()
        labels = load_labels(args.labels)

        #cap = cv2.VideoCapture('videotestsrc ! video/x-raw,framerate=20/1 ! videoscale ! videoconvert ! appsink', cv2.CAP_GSTREAMER)
        cap = cv2.VideoCapture(args.camera_idx)
            
        #cap.set(3, 1920)
        #cap.set(4, 1440)
        # 4:3 resolutions
        # 640×480, 800×600, 960×720, 1024×768, 1280×960, 1400×1050,
        # 1440×1080 , 1600×1200, 1856×1392, 1920×1440, 2048×1536
        # 5 MP
        cap.set(3, 2048)
        cap.set(4, 1536)
        
        bboxes = []
        colors = [] 
        visitation = []
        trackers = []
        started_tracking = None
        last_tracked = None
        visitation_id = None
        recording = False
        out = None
        fps = FPS().start()
        is_stopped = False
        current_fps = 4.0
        boxes = []
        photo_per_visitation_count = 0
        photo_per_visitation_max = 10
        full_photo_per_visitation_max = 1
        full_photo_per_visitation_count = 0

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
                cv2_im_rgb = cv2.cvtColor(cv2_im, cv2.COLOR_BGR2RGB)
                pil_im = Image.fromarray(cv2_im)

                success, boxes = multiTracker.update(cv2_im)
                if success:
                    last_tracked = time.time()
                
                if len(boxes) > 0:
                    logging.info("success {}".format(success))
                    logging.info("boxes {}".format(boxes))

                common.set_input(interpreter, pil_im)
                interpreter.invoke()
                objs = get_output(interpreter, score_threshold=args.threshold, top_k=args.top_k)
                height, width, channels = cv2_im.shape
                
                bird_detected = False
                boxes_to_draw = []
                for obj in objs:
                    x0, y0, x1, y1 = list(obj.bbox)
                    x0, y0, x1, y1 = int(x0*width), int(y0*height), int(x1*width), int(y1*height)
                    percent = int(100 * obj.score)
                    object_label = labels.get(obj.id, obj.id)
                    label = '{}% {}'.format(percent, object_label)
                    
                    if object_label == 'bird' and percent > 20:
                        bird_detected = True
                        new_bird = True
                        
                        for bbox in boxes:
                            if intersects(bbox, obj.bbox):
                                logging.info("intersected.. same bird")
                                new_bird = False
                        
                        if new_bird and len(bboxes) == 0:
                            logging.info("found a new bird")
                            visitation_id =  uuid.uuid4()
                            started_tracking = time.time()
                            recording = True
                            bboxes.append(obj.bbox)
                            colors.append((randint(64, 255), randint(64, 255), randint(64, 255)))
                            tracker = cv2.TrackerCSRT_create()
                            trackers.append(tracker)
                            multiTracker.add(tracker, cv2_im, obj.bbox)
                            
                        if disk_has_space() and photo_per_visitation_count <= photo_per_visitation_max:
                            directory = "storage/detected/{}/{}".format(time.strftime("%Y-%m-%d"), visitation_id)
                            if not os.path.exists(directory):
                                os.makedirs(directory)
                            boxed_image_path = "{}/boxed_{}_{}.png".format(directory, time.strftime("%H-%M-%S"), percent)
                            cv2.imwrite( boxed_image_path, cv2_im[y0:y1,x0:x1] )
                            photo_per_visitation_count = photo_per_visitation_count + 1

                        else:
                            logging.info("Not enough disk space")

                    percent = int(100 * obj.score)
                    object_label = labels.get(obj.id, obj.id)
                    label = '{}% {}'.format(percent, object_label)

                    # postpone drawing so we don't get lines in the photos
                    boxes_to_draw.append({
                        "p1": (x0, y0),
                        "p2": (x1, y1),
                        "label": label,
                        "label_p": (x0, y0+30)
                    })

                for box in boxes_to_draw:
                        if label == "bird":
                            cv2_im = cv2.rectangle(cv2_im, box["p1"], box["p2"], (169, 68, 66), 5)
                            cv2_im = cv2.putText(cv2_im, box["label"], box["label_p"],
                                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, (169, 68, 66), 5)

                if disk_has_space() and full_photo_per_visitation_count <= full_photo_per_visitation_max:
                    directory = "storage/detected/{}/{}".format(time.strftime("%Y-%m-%d"), visitation_id)
                    if not os.path.exists(directory):
                        os.makedirs(directory)
                    full_image_path = "{}/full_{}.png".format(directory, time.strftime("%H-%M-%S"))
                    full_photo_per_visitation_count = full_photo_per_visitation_count + 1
                    cv2.imwrite( full_image_path, cv2_im ) 

                # if recording == True and disk_has_space():
                #     if out == None:
                #         fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                #         out = cv2.VideoWriter("storage/video/{}.mp4".format(visitation_id), fourcc, 4.0, (2048,1536))
                #         #out = cv2.VideoWriter('appsrc ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay ! udpsink host=127.0.0.1 port=5000',cv2.CAP_GSTREAMER,0, 20, (2048,1536), True)
                #     out.write(cv2_im)
                    
                if bird_detected == False and len(trackers) > 0:
                    now = time.time()
                    if now - last_tracked > 60:
                        logging.info("visitation {} lasted {} seconds".format(visitation_id, now - started_tracking))
                        logging.info("clearing trackers")
                        for tracker in trackers:
                            tracker.clear()
                        multiTracker = cv2.MultiTracker_create()
                        boxes = []
                        colors = []
                        trackers = []
                        bboxes = []
                        photo_per_visitation_count = 0
                        recording = False
                        if out is not None:
                            out.release()
                            out = None

                for i, newbox in enumerate(boxes):
                    x0, y0, x1, y1 = list(newbox)
                    x0, y0, x1, y1 = int(x0*width), int(y0*height), int(x1*width), int(y1*height)
                    cv2_im = cv2.rectangle(cv2_im, (x0, y0), (x1, y1), (0, 0, 255), 2)
                
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
