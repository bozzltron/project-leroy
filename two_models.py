# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Demo to show running two models on one/two Edge TPU devices.

This is a dummy example that compares running two different models using one
Edge TPU vs two Edge TPUs. It requires that your system includes two Edge TPU
devices.

You give the script one classification model and one
detection model, and it runs each model the number of times specified with the
`num_inferences` argument, using the same image. It then reports the time
spent using either one or two Edge TPU devices.

Note: Running two models alternatively with one Edge TPU is cache unfriendly,
as each model continuously kicks the other model off the device's cache when
they each run. In this case, running several inferences with one model in a
batch before switching to another model can help to some extent. It's also
possible to co-compile both models so they can be cached simultaneously
(if they fit; read more at coral.ai/docs/edgetpu/compiler/). But using two
Edge TPUs with two threads can help more.
"""

import argparse
import contextlib
import threading
import time
import imutils
import time
import cv2

from edgetpu.basic import edgetpu_utils
from edgetpu.classification.engine import ClassificationEngine
from edgetpu.detection.engine import DetectionEngine
import numpy as np
from PIL import Image
from imutils.video import VideoStream


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


def run_two_models_two_tpus(classification_model, detection_model, image_name,
                            num_inferences):
  """Runs two models using two Edge TPUs with two threads.

  Args:
    classification_model: string, path to classification model
    detection_model: string, path to detection model.
    image_name: string, path to input image.
    num_inferences: int, number of inferences to run for each model.

  Returns:
    double, wall time it takes to finish the job.
  """

  def classification_job(classification_model, image_name, num_inferences):
    """Runs classification job."""
    engine = ClassificationEngine(classification_model)
    with open_image(image_name) as image:
      tensor = get_input_tensor(engine, image)

    # Using `classify_with_input_tensor` to exclude image down-scale cost.
    for _ in range(num_inferences):
      engine.classify_with_input_tensor(tensor, top_k=1)

  def detection_job(detection_model, image_name, num_inferences):
    """Runs detection job."""
    engine = DetectionEngine(detection_model)
    with open_image(image_name) as img:
      # Resized image.
      _, height, width, _ = engine.get_input_tensor_shape()
      tensor = np.asarray(img.resize((width, height), Image.NEAREST)).flatten()

    # Using `detect_with_input_tensor` to exclude image down-scale cost.
    for _ in range(num_inferences):
      engine.detect_with_input_tensor(tensor, top_k=1)

  start_time = time.perf_counter()
  classification_thread = threading.Thread(
      target=classification_job,
      args=(classification_model, image_name, num_inferences))
  detection_thread = threading.Thread(
      target=detection_job, args=(detection_model, image_name, num_inferences))

  classification_thread.start()
  detection_thread.start()
  classification_thread.join()
  detection_thread.join()
  return time.perf_counter() - start_time


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--classification_model', help='Path of classification model.', required=False, default='all_models/mobilenet_v2_1.0_224_inat_bird_quant_edgetpu.tflite')
  parser.add_argument('--detection_model', help='Path of detection model.', required=False, default='all_models/mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite')
  parser.add_argument('--image', help='Path of the image.', required=False)
  parser.add_argument('--classification_labels', required=False, default='all_models/coco_labels.txt')
  parser.add_argument('--detection_labels', required=False, default='all_models/inat_birds_labels.txt')
  args = parser.parse_args()

  edge_tpus = edgetpu_utils.ListEdgeTpuPaths(
      edgetpu_utils.EDGE_TPU_STATE_UNASSIGNED)
  
  # initialize the video stream and allow the camera sensor to warmup
  print("[INFO] starting video stream...")
  vs = VideoStream(src=0, resolution=(2048, 1536)).start()
  #vs = VideoStream(usePiCamera=False).start()
  time.sleep(2.0)

  detection_model = DetectionEngine(args.detection_model)
  classification_model = ClassificationEngine(args.classification_model)

  detection_labels = args.detection_labels
  classification_labels = args.classification_labels

  # loop over the frames from the video stream
  while True:
    # grab the frame from the threaded video stream and resize it
    # to have a maximum width of 500 pixels
    frame = vs.read()
    frame = imutils.resize(frame, width=500)
    orig = frame.copy()
    # prepare the frame for classification by converting (1) it from
    # BGR to RGB channel ordering and then (2) from a NumPy array to
    # PIL image format
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = Image.fromarray(frame)

    # make predictions on the input frame
    start = time.time()
    results = detection_model.ClassifyWithImage(frame, top_k=1)
    end = time.time()

    # ensure at least one result was found
    if len(results) > 0:
      # draw the predicted class label, probability, and inference
      # time on the output frame
      (classID, score) = results[0]
      text = "{}: {:.2f}% ({:.4f} sec)".format(detection_labels[classID],
        score * 100, end - start)
      cv2.putText(orig, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
        0.5, (0, 0, 255), 2)
    # show the output frame and wait for a key press
    cv2.imshow("Frame", orig)
    key = cv2.waitKey(1) & 0xFF
    # if the `q` key was pressed, break from the loop
    if key == ord("q"):
      break
  # do a bit of cleanup
  cv2.destroyAllWindows()
  vs.stop()

if __name__ == '__main__':
  main()
