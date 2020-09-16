import cv2 
import uuid
import logging 
import time
from photo import capture
from random import randint

#Initialize logging files
logging.basicConfig(filename='storage/results.log',
                    format='%(asctime)s-%(message)s',
                    level=logging.DEBUG)

class Visitations:
    visitations = []
    #multiTracker = cv2.MultiTracker_create()
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
    vistation_max_seconds = 300.0

    def intersects(box1, box2):
        logging.info("box1 {}".format(box1))
        logging.info("box2 {}".format(box2))
        box1x0, box1y0, box1x1, box1y1 = list(box1)
        box2x0, box2y0, box2x1, box2y1 = list(box2)
        return not (box1x0 < box2x1 or box1x1 > box2x0 or box1y0 < box2y1 or box1y1 > box2y0)

    def bb_intersection_over_union(boxA, boxB):
        # determine the (x, y)-coordinates of the intersection rectangle
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        # compute the area of intersection rectangle
        interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
        # compute the area of both the prediction and ground-truth
        # rectangles
        boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
        boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)
        # compute the intersection over union by taking the intersection
        # area and dividing it by the sum of prediction + ground-truth
        # areas - the interesection area
        iou = interArea / float(boxAArea + boxBArea - interArea)
        # return the intersection over union value
        return iou

    def update(self, objs, frame, labels):
        height, width, channels = frame.shape

        bird_detected = False
        boxes_to_draw = []
        object_label = ""
        for obj in objs:
            if hasattr(obj, 'bbox'):
                # handle tflite result
                x0, y0, x1, y1 = list(obj.bbox)
                x0, y0, x1, y1 = int(x0*width), int(y0*height), int(x1*width), int(y1*height)
                object_label = labels.get(obj.id, obj.id)
            else:
                # handle edgetpu result
                box = obj.bounding_box
                p0, p1 = list(box)
                x0, y0 = list(p0)
                x1, y1 = list(p1)
                object_label = labels[obj.label_id]
            percent = int(100 * obj.score)
            
            label = '{}% {}'.format(percent, object_label)
            
            if object_label == 'bird' and percent > 20:
                bird_detected = True
                new_bird = True
                
                if new_bird and time.time() - self.started_tracking < self.vistation_max_seconds:
                    logging.info("found a new bird")
                    started_tracking = time.time()
                    self.visitation_id = self.add(obj, frame)
                    logging.info("visitation id {}".format(self.visitation_id))
                    
                if self.photo_per_visitation_count <= self.photo_per_visitation_max:
                    logging.info('saving photo {}, {}, {}, {}'.format([y0, y1, x0, x1], self.visitation_id, percent, 'boxed'))
                    capture(frame[int(y0):int(y1),int(x0):int(x1)], self.visitation_id, percent, 'boxed')
                    logging.info("saved boxed image {} of {}".format(self.photo_per_visitation_count, self.photo_per_visitation_max))
                    self.photo_per_visitation_count = self.photo_per_visitation_count + 1

            percent = int(100 * obj.score)
            label = '{}% {}'.format(percent, object_label)

            # postpone drawing so we don't get lines in the photos
            box = {
                "p1": (x0, y0),
                "p2": (x1, y1),
                "label": label,
                "label_p": (x0, y0+30)
            }
            logging.info("Adding box to draw {}".format(box))
            boxes_to_draw.append()

        logging.info("Boxes to draw {}".format(boxes_to_draw))
        for box in boxes_to_draw:
            if box["label"] == "bird":
                frame = cv2.rectangle(frame, box["p1"], box["p2"], (169, 68, 66), 5)
                frame = cv2.putText(frame, box["label"], box["label_p"], cv2.FONT_HERSHEY_SIMPLEX, 2.0, (169, 68, 66), 5)

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
            
        # extend visitation if birds are still present
        if time.time() - self.started_tracking > self.vistation_max_seconds:
            logging.info("Extending visitation by 60")
            if bird_detected == True:
                self.started_tracking = time.time() + 60
            else:
                self.reset()
          

    def add(self, obj, frame):
        visitation = Visitation()
        visitation.start()
        recording = True          
        return visitation.id

    def reset(self):
        logging.info("visitation id {} over".format(self.visitation_id))
        self.visitations = []
        self.photo_per_visitation_count = 0
        self.full_photo_per_visitation_count = 0
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