import uuid
import logging
import time
from photo import capture
from random import randint

# Initialize logging files
logging.basicConfig(filename='storage/results.log',
                    format='%(asctime)s-%(message)s',
                    level=logging.DEBUG)

def add_padding_to_bbox(bbox, image_width, image_height, padding):
    x1, y1, x2, y2 = bbox
    
    # Calculate the new coordinates with padding
    new_x1 = max(0, x1 - padding)
    new_y1 = max(0, y1 - padding)
    new_x2 = min(image_width - 1, x2 + padding)
    new_y2 = min(image_height - 1, y2 + padding)
    
    return (new_x1, new_y1, new_x2, new_y2)
class Visitations:
    boxes = []
    success = False
    photo_per_visitation_count = 0
    photo_per_visitation_max = 10
    full_photo_per_visitation_max = 1
    full_photo_per_visitation_count = 0
    last_tracked = None
    started_tracking = None
    visitation_id = None
    vistation_max_seconds = float(300)

    def update(self, objs, frame, labels):
        height, width, channels = frame.shape

        bird_detected = False
        object_label = ""
        percent = 0  # Initialize percent
        for obj in objs:
            x0, y0, x1, y1 = list(obj.bbox)
            object_label = labels.get(obj.id, obj.id)
            percent = int(100 * obj.score)
            x0, y0, x1, y1 = int(x0*width), int(y0*height), int(x1*width), int(y1*height)

            if object_label == 'bird' and percent > 40:
                bird_detected = True
                
                if self.visitation_id is None:
                    self.visitation_id = self.add(obj, frame)
                    self.started_tracking = time.time()
                    logging.info("visitation {} started".format(self.visitation_id))
                    
                if time.time() - self.started_tracking < self.vistation_max_seconds:
                    if self.photo_per_visitation_count < self.photo_per_visitation_max:
                        logging.info('full height {}, full width {}'.format(height, width))
                        logging.info('saving photo {}, {}, {}, {}'.format([y0, y1, x0, x1], self.visitation_id, percent, 'boxed'))
                        frame_without_boxes = frame.copy()
                        padded_x0, padded_y0, padded_x1, padded_y1 = add_padding_to_bbox([x0, y0, x1, y1], width, height, 50)
                        # Get frame resolution
                        height, width = frame_without_boxes.shape[:2]
                        resolution = (width, height)
                        bbox = (padded_x0, padded_y0, padded_x1, padded_y1)
                        capture(
                            frame_without_boxes[int(padded_y0):int(padded_y1), int(padded_x0):int(padded_x1)], 
                            self.visitation_id, 
                            obj.score,  # Pass as float 0-1, not percent
                            'boxed',
                            resolution=resolution,
                            detection_bbox=bbox
                        )
                        logging.info("saved boxed image {} of {}".format(self.photo_per_visitation_count, self.photo_per_visitation_max))
                        self.photo_per_visitation_count = self.photo_per_visitation_count + 1
                else:
                    if bird_detected:
                        logging.info("Extending visitation by 60")
                        self.started_tracking = time.time() + 60
                    else:
                        self.reset()

        # If no bird detected and past timeout, end visitation
        if not bird_detected and self.visitation_id and self.started_tracking:
            if time.time() - self.started_tracking >= self.vistation_max_seconds:
                self.reset()

        if self.full_photo_per_visitation_count < self.full_photo_per_visitation_max:
            if self.visitation_id:
                # Get frame resolution
                height, width = frame.shape[:2]
                resolution = (width, height)
                capture(
                    frame, 
                    self.visitation_id, 
                    percent / 100.0,  # Convert percent to float 0-1
                    'full',
                    resolution=resolution
                )
                logging.info("saved full image {} of {}".format(self.full_photo_per_visitation_count, self.full_photo_per_visitation_max))
                self.full_photo_per_visitation_count = self.full_photo_per_visitation_count + 1

    def add(self, obj, frame):
        visitation = Visitation()
        visitation.start()
        return visitation.id

    def reset(self):
        logging.info("visitation id {} over".format(self.visitation_id))
        self.photo_per_visitation_count = 0
        self.full_photo_per_visitation_count = 0
        self.visitation_id = None


class Visitation:
    start_time = None
    end_time = None
    tracker = None

    def __init__(self):
        self.id = uuid.uuid4()
        self.color = randint(64, 255), randint(64, 255), randint(64, 255)

    def end(self, timestamp):
        self.end_time = timestamp

    def start(self, timestamp=time.time()):
        self.start_time = timestamp

    def duration(self):
        return self.end_time - self.start_time
