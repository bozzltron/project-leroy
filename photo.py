import cv2
import psutil
import os
import time 

class Photo:

    def clarity(self, image):
        # compute the Laplacian of the image and then return the focus
        # measure, which is simply the variance of the Laplacian
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return 0 if image is None else cv2.Laplacian(gray, cv2.CV_64F).var()

    def is_focused(self, image):
        return clarity(image) > 100

    def has_disk_space(self):
        hdd = psutil.disk_usage('/')
        return hdd.percent < 95

    def capture(self, frame, visitation_id, detection_score, photo_type):
        if has_disk_space():
            directory = "storage/detected/{}/{}".format(time.strftime("%Y-%m-%d"), visitation_id)
            if not os.path.exists(directory):
                os.makedirs(directory)
            boxed_image_path = "{}/{}_{}_{}.png".format(directory, photo_type, time.strftime("%H-%M-%S"), detection_score)
            cv2.imwrite( boxed_image_path, frame )
