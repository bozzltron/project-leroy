import cv2 
import uuid
import logging 
import time
from photo import Photo
from random import randint

#Initialize logging files
logging.basicConfig(filename='storage/results.log',
                    format='%(asctime)s-%(message)s',
                    level=logging.DEBUG)

class Visitations:
    visitations = []
    multiTracker = cv2.MultiTracker_create()
    boxes = []
    success = False
    photo_per_visitation_count = 0
    photo_per_visitation_max = 10
    full_photo_per_visitation_max = 1
    full_photo_per_visitation_count = 0
    bboxes = []
    recording = False
    out = None
    last_tracked = None
    started_tracking = None
    visitation_id = None

    def intersects(box1, box2):
        logging.info("box1 {}".format(box1))
        logging.info("box2 {}".format(box2))
        box1x0, box1y0, box1x1, box1y1 = list(box1)
        box2x0, box2y0, box2x1, box2y1 = list(box2)
        return not (box1x0 < box2x1 or box1x1 > box2x0 or box1y0 < box2y1 or box1y1 > box2y0)
    
    def draw_tracking_boxes(self, boxes, frame):
        height, width, channels = frame.shape
        for i, newbox in enumerate(boxes):
            x0, y0, x1, y1 = list(newbox)
            x0, y0, x1, y1 = int(x0*width), int(y0*height), int(x1*width), int(y1*height)
            frame = cv2.rectangle(frame, (x0, y0), (x1, y1), (0, 0, 255), 2)

    def update(self, objs, frame, labels):
        self.success, self.boxes = self.multiTracker.update(frame)
        height, width, channels = frame.shape
        self.draw_tracking_boxes(self.boxes, frame)

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
                
                if new_bird and len(self.bboxes) == 0:
                    logging.info("found a new bird")
                    started_tracking = time.time()
                    self.visitation_id = self.add(obj, frame)
                    
                if self.photo_per_visitation_count <= self.photo_per_visitation_max:
                    Photo.capture(frame[y0:y1,x0:x1], self.visitation_id, percent, 'boxed')
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
            if box["label"] == "bird":
                frame = cv2.rectangle(frame, box["p1"], box["p2"], (169, 68, 66), 5)
                frame = cv2.putText(frame, box["label"], box["label_p"], cv2.FONT_HERSHEY_SIMPLEX, 2.0, (169, 68, 66), 5)

        if self.full_photo_per_visitation_count <= self.full_photo_per_visitation_max:
            if self.visitation_id:
                Photo.capture(frame, self.visitation_id, percent, 'full')
                full_photo_per_visitation_count = full_photo_per_visitation_count + 1

        # if recording == True and disk_has_space():
        #     if out == None:
        #         fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        #         out = cv2.VideoWriter("storage/video/{}.mp4".format(self.visitation_id), fourcc, 4.0, (2048,1536))
        #         #out = cv2.VideoWriter('appsrc ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay ! udpsink host=127.0.0.1 port=5000',cv2.CAP_GSTREAMER,0, 20, (2048,1536), True)
        #     out.write(frame)
            
        if bird_detected == False and len(self.visitations) > 0:
            now = time.time()
            if now - last_tracked > 60:
                self.reset()

    def add(self, obj, frame):
        visitation = Visitation()
        visitation.start()
        recording = True
        self.bboxes.append(obj.bbox)   
        width = obj.bbox.xmax-obj.bbox.xmin
        height = obj.bbox.ymax-obj.bbox.ymin
        self.multiTracker.add(visitation.tracker, frame, (obj.bbox.xmin, obj.bbox.ymin, width/2, height/2))            
        return visitation.id

    def reset(self):
        logging.info("clearing trackers")
        for visit in self.visitations:
            visit.tracker.clear()
        self.visitations = []
        self.multiTracker = cv2.MultiTracker_create()
        boxes = []
        self.bboxes = []
        photo_per_visitation_count = 0
        full_photo_per_visitation_count = 0
        recording = False
        if self.out is not None:
            self.out.release()
            self.out = None   

class Visitation:
    start_time = None
    end_time = None
    id =  uuid.uuid4()
    color = randint(64, 255), randint(64, 255), randint(64, 255)
    tracker = None

    def __init__(self):
        self.tracker = cv2.TrackerCSRT_create()

    def end(self, timestamp):
        self.end_time = timestamp

    def start(self, timestamp=time.time()):
        self.start_time = timestamp

    def duration(self):
        return self.end_time - self.start_time