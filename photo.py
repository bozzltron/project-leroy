import cv2
import psutil
import os
import time 
import logging 
import threading

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

def capture(frame, visitation_id, detection_score, photo_type):
    thread = threading.Thread(target=save, args=(frame, visitation_id, detection_score, photo_type))
    logging.info("Main : before running thread")
    thread.start()

def mkdirs(visitation_id):
    directory = "storage/detected/{}/{}".format(time.strftime("%Y-%m-%d"), visitation_id)
    logging.info("making directories")
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory

def save(frame, visitation_id, detection_score, photo_type, y1=None, y0=None, x1=None, x0=None):
    logging.info('checking disk space')
    try:
        if has_disk_space():
            directory = mkdirs(visitation_id)
            image_path = "{}/{}_{}_{}.png".format(directory, photo_type, time.strftime("%H-%M-%S"), detection_score)
            logging.info("writing image {}".format(image_path))
            
            cap = cv2.VideoCapture(0)
            cap.set(3,3264) 
            cap.set(4,2448)
            if cap.isOpened():
                logging.info("capture 8MP image")
                _,image = cap.read()
                cap.release() 
            if y1 and y0 and x1 and x0:
                logging.info("crop 8MP image")
                height, width, channels = image.shape
                image = image[y1*height:y0*height,x1*width:x0*width]
            cv2.imwrite( image_path, image )
    except:
        logging.exception("Failed to save image")