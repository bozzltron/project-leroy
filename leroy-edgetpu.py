#!/usr/bin/env python3
import argparse
import contextlib
import threading
import time
import imutils
import time
import cv2
import re

from edgetpu.basic import edgetpu_utils
from edgetpu.classification.engine import ClassificationEngine
from edgetpu.detection.engine import DetectionEngine
import numpy as np
from PIL import Image
from imutils.video import VideoStream
from visitations import Visitations

@contextlib.contextmanager
def open_image(path):
  with open(path, 'rb') as f:
    with Image.open(f) as image:
      yield image


def get_input_tensor(engine, image):
  _, height, width, _ = engine.get_input_tensor_shape()
  return np.asarray(image.resize((width, height), Image.NEAREST)).flatten()


def run_two_models_one_tpu(classification_model, detection_model, image_name,
                           num_inferences, batch_size):
  """Runs two models ALTERNATIVELY using one Edge TPU.

  It runs classification model `batch_size` times and then switch to run
  detection model `batch_size` time until each model is run `num_inferences`
  times.

  Args:
    classification_model: string, path to classification model
    detection_model: string, path to detection model.
    image_name: string, path to input image.
    num_inferences: int, number of inferences to run for each model.
    batch_size: int, indicates how many inferences to run one model before
      switching to the other one.

  Returns:
    double, wall time it takes to finish the job.
  """
  start_time = time.perf_counter()
  engine_a = ClassificationEngine(classification_model)
  # `engine_b` shares the same Edge TPU as `engine_a`
  engine_b = DetectionEngine(detection_model, engine_a.device_path())
  with open_image(image_name) as image:
    # Resized image for `engine_a`, `engine_b`.
    tensor_a = get_input_tensor(engine_a, image)
    tensor_b = get_input_tensor(engine_b, image)

  num_iterations = (num_inferences + batch_size - 1) // batch_size
  for _ in range(num_iterations):
    # Using `classify_with_input_tensor` and `detect_with_input_tensor` on purpose to
    # exclude image down-scale cost.
    for _ in range(batch_size):
      engine_a.classify_with_input_tensor(tensor_a, top_k=1)
    for _ in range(batch_size):
      engine_b.detect_with_input_tensor(tensor_b, top_k=1)
  return time.perf_counter() - start_time


def classification_job(classification_model, image, num_inferences):
  """Runs classification job."""
  classification = classification_model.classify_with_image(image, top_k=num_inferences)
  print("classification {}".format(classification)) 

def load_labels(path):
    p = re.compile(r'\s*(\d+)(.+)')
    with open(path, 'r', encoding='utf-8') as f:
       lines = (p.match(line).groups() for line in f.readlines())
       return {int(num): text.strip() for num, text in lines}

def intersects(box1, box2):
  print("box1 {}".format(box1))
  print("box2 {}".format(box2))
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

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--classification_model', help='Path of classification model.', required=False, default='all_models/mobilenet_v2_1.0_224_inat_bird_quant_edgetpu.tflite')
  parser.add_argument('--detection_model', help='Path of detection model.', required=False, default='all_models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite')
  parser.add_argument('--image', help='Path of the image.', required=False)
  parser.add_argument('--classification_labels', required=False, default='all_models/inat_bird_labels.txt')
  parser.add_argument('--detection_labels', required=False, default='all_models/coco_labels.txt')
  args = parser.parse_args()
  
  # initialize the video stream and allow the camera sensor to warmup
  print("[INFO] starting video stream...")
  vs = VideoStream(src=0, usePiCamera=True, resolution=(3264, 2448)).start()
  #vs = VideoStream(usePiCamera=False).start()
  time.sleep(2.0)

  detection_model = DetectionEngine(args.detection_model)
  classification_model = ClassificationEngine(args.classification_model)
  
  detection_labels = load_labels(args.detection_labels)
  print("detection_labels : {}".format(len(detection_labels)))
  classification_labels = load_labels(args.classification_labels)

  visitations = Visitations()

  # loop over the frames from the video stream
  while True:
    # grab the frame from the threaded video stream and resize it
    # to have a maximum width of 500 pixels
    frame = vs.read()
    #resized_frame = imutils.resize(frame, width=500)
    # prepare the frame for classification by converting (1) it from
    # BGR to RGB channel ordering and then (2) from a NumPy array to
    # PIL image format
    resized_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resized_frame = Image.fromarray(resized_frame)
    objs = detection_model.detect_with_image(resized_frame, top_k=3)

    visitations.update(objs, frame, detection_labels)

    # show the output frame and wait for a key press
    cv2.namedWindow("Leroy", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Leroy", 800, 600)
    cv2.imshow("Leroy", frame)
    key = cv2.waitKey(1) & 0xFF
    # if the `q` key was pressed, break from the loop
    if key == ord("q"):
      break
  # do a bit of cleanup
  cv2.destroyAllWindows()
  vs.stop()

if __name__ == '__main__':
  main()
