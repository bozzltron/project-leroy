import cv2
import psutil
import os
import time 
import logging 
import threading
from picamera import PiCamera

#Initialize logging files
logging.basicConfig(filename='storage/results.log',
                    format='%(asctime)s-%(message)s',
                    level=logging.DEBUG)

def clarity(self, image):
    # compute the Laplacian of the image and then return the focus
    # measure, which is simply the variance of the Laplacian
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return 0 if image is None else cv2.Laplacian(gray, cv2.CV_64F).var()

def is_focused(self, image):
    return clarity(image) > 100

def has_disk_space():
    hdd = psutil.disk_usage('/')
    return hdd.percent < 95

def capture(frame, visitation_id, detection_score, photo_type, bounding_box=None):
    thread = threading.Thread(target=save, args=(frame, visitation_id, detection_score, photo_type, bounding_box))
    logging.info("Main : before running thread")
    thread.start()

def mkdirs(visitation_id):
    directory = "storage/detected/{}/{}".format(time.strftime("%Y-%m-%d"), visitation_id)
    logging.info("making directories")
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory

def save(frame, visitation_id, detection_score, photo_type):
    logging.info('checking disk space')
    try:
        if has_disk_space():
            directory = mkdirs(visitation_id)
            image_path = "{}/{}_{}_{}.png".format(directory, photo_type, time.strftime("%H-%M-%S"), detection_score)
            logging.info("writing image {}".format(image_path))
            cv2.imwrite( image_path, frame )
            # camera = PiCamera()
            # camera.resolution = (3264, 2448)
            # if bounding_box:
            #     logging.info("zooming image")
            #     camera.zoom = (bounding_box['x0'], bounding_box['y0'], bounding_box['x1']-bounding_box['x0'], bounding_box['y1']-bounding_box['y0'])

            # camera.capture( image_path , 'png')

    except:
        logging.exception("Failed to save image")