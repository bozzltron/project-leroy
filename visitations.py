import cv2 
import uuid
import logging 
import time
import os
from photo import capture
from random import randint
from imutils.video import VideoStream

#Initialize logging files
logging.basicConfig(filename='storage/results.log',
                    format='%(asctime)s-%(message)s',
                    level=logging.DEBUG)

class Visitations:
    boxes = []
    success = False
    photo_per_visitation_count = 0
    photo_per_visitation_max = 10
    full_photo_per_visitation_max = 1
    full_photo_per_visitation_count = 0
    recording = False
    out = None
    last_tracked = None
    started_tracking = None
    visitation_id = None
    vistation_max_seconds = float(300)

    def update(self, objs, frame, labels):
        height, width, channels = frame.shape

        bird_detected = False
        boxes_to_draw = []
        object_label = ""
        for obj in objs:
            if hasattr(obj, 'bbox'):
                # handle tflite result
                x0, y0, x1, y1 = list(obj.bbox)
                object_label = labels.get(obj.id, obj.id)
            else:
                # handle edgetpu result
                box = obj.bounding_box
                p0, p1 = list(box)
                x0, y0 = list(p0)
                x1, y1 = list(p1)
                object_label = labels[obj.label_id]
            percent = int(100 * obj.score)
            x0, y0, x1, y1 = int(x0*width), int(y0*height), int(x1*width), int(y1*height)

            label = '{}% {}'.format(percent, object_label)
            
            if object_label == 'bird' and percent > 40:
                bird_detected = True
                
                if self.visitation_id == None:
                    self.visitation_id = self.add(obj, frame)
                    self.started_tracking = time.time()
                    logging.info("visitation {} started".format(self.visitation_id))
                    
                if time.time() - self.started_tracking < self.vistation_max_seconds:
                    if self.photo_per_visitation_count <= self.photo_per_visitation_max:
                        logging.info('full height {}, full width {}'.format(height, width))
                        logging.info('saving photo {}, {}, {}, {}'.format([y0, y1, x0, x1], self.visitation_id, percent, 'boxed'))
                        frame_without_boxes = frame.copy()
                        capture(frame_without_boxes[int(y0):int(y1),int(x0):int(x1)], self.visitation_id, percent, 'boxed')
                        logging.info("saved boxed image {} of {}".format(self.photo_per_visitation_count, self.photo_per_visitation_max))
                        self.photo_per_visitation_count = self.photo_per_visitation_count + 1
                else:
                    if bird_detected == True:
                        logging.info("Extending visitation by 60")
                        self.started_tracking = time.time() + 60
                    else:
                        self.reset()

            percent = int(100 * obj.score)
            label = '{}% {}'.format(percent, object_label)

            # postpone drawing so we don't get lines in the photos
            box = {
                "p1": (x0*width, y0*height),
                "p2": (x1*width, y1*height),
                "label": label,
                "label_p": (x0, y0+30)
            }
            boxes_to_draw.append(box)

        for box in boxes_to_draw:
            if "bird" in box["label"]:
                frame = cv2.rectangle(frame, box["p1"], box["p2"], (169, 68, 66), 2)
                #frame = cv2.putText(frame, box["label"], box["label_p"], cv2.FONT_HERSHEY_SIMPLEX, 1.0, (169, 68, 66), 3)

        if self.full_photo_per_visitation_count <= self.full_photo_per_visitation_max:
            if self.visitation_id:
                capture(frame, self.visitation_id, percent, 'full')
                logging.info("saved full image {} of {}".format(self.full_photo_per_visitation_count, self.full_photo_per_visitation_max))
                self.full_photo_per_visitation_count = self.full_photo_per_visitation_count + 1

        # if recording == True and disk_has_space():
        #     if out == None:
        #         fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        #         out = cv2.VideoWriter("storage/video/{}.mp4".format(self.visitation_id), fourcc, 4.0, (2048,1536))
        #         #out = cv2.VideoWriter('appsrc ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay ! udpsink host=127.0.0.1 port=5000',cv2.CAP_GSTREAMER,0, 20, (2048,1536), True)
        #     out.write(frame)      

    def add(self, obj, frame):
        visitation = Visitation()
        visitation.start()
        recording = True          
        return visitation.id

    def reset(self):
        logging.info("visitation id {} over".format(self.visitation_id))
        self.photo_per_visitation_count = 0
        self.full_photo_per_visitation_count = 0
        self.visitation_id = None
        recording = False
        if self.out is not None:
            self.out.release()
            self.out = None   

class Visitation:
    start_time = None
    end_time = None
    tracker = None

    def __init__(self):
        self.id =  uuid.uuid4()
        self.color = randint(64, 255), randint(64, 255), randint(64, 255)

    def end(self, timestamp):
        self.end_time = timestamp

    def start(self, timestamp=time.time()):
        self.start_time = timestamp

    def duration(self):
        return self.end_time - self.start_time