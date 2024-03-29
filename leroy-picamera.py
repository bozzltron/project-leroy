#!/usr/bin/env python3
import argparse
import os
import sys
import logging
from PIL import Image
import cv2
import numpy as np
import imutils
from visitations import Visitations
from pycoral.utils.edgetpu import make_interpreter
from pycoral.utils.dataset import read_label_file
import picamera
from picamera.array import PiRGBArray

print("cv version" + cv2.__version__)

Object = collections.namedtuple('Object', ['id', 'score', 'bbox'])

# Initialize logging files
logging.basicConfig(filename='storage/results.log',
                    format='%(asctime)s-%(message)s',
                    level=logging.DEBUG)

def load_labels(path):
    p = re.compile(r'\s*(\d+)(.+)')
    with open(path, 'r', encoding='utf-8') as f:
        lines = (p.match(line).groups() for line in f.readlines())
        return {int(num): text.strip() for num, text in lines}

class BBox(collections.namedtuple('BBox', ['xmin', 'ymin', 'xmax', 'ymax'])):
    """Bounding box.
    Represents a rectangle whose sides are either vertical or horizontal, parallel
    to the x or y-axis.
    """
    __slots__ = ()

def get_output(interpreter, score_threshold, top_k, image_scale=1.0):
    """Returns a list of detected objects."""
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

def main():
    try:
        default_model_dir = 'all_models'
        default_model = 'ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite'
        default_labels = 'coco_labels.txt'
        parser = argparse.ArgumentParser()
        parser.add_argument('--model', help='.tflite model path',
                            default=os.path.join(default_model_dir, default_model))
        parser.add_argument('--labels', help='label file path',
                            default=os.path.join(default_model_dir, default_labels))
        parser.add_argument('--top_k', type=int, default=3,
                            help='number of categories with the highest score to display')
        parser.add_argument('--threshold', type=float, default=0.1,
                            help='classifier score threshold')
        args = parser.parse_args()

        # Initialize logging files
        logging.basicConfig(filename='storage/results.log',
                            format='%(asctime)s-%(message)s',
                            level=logging.DEBUG)

        print('Loading {} with {} labels.'.format(args.model, args.labels))
        interpreter = make_interpreter(args.model)
        interpreter.allocate_tensors()
        labels = read_label_file(args.labels)

        with picamera.PiCamera() as camera:
            camera.resolution = (2048, 1536)
            camera.framerate = 30
            raw_capture = PiRGBArray(camera, size=(2048, 1536))

            visitations = Visitations()

            for frame in camera.capture_continuous(raw_capture, format="bgr", use_video_port=True):
                try:
                    cv2_im = frame.array
                    resized_frame = imutils.resize(cv2_im, width=500)
                    pil_im = Image.fromarray(resized_frame)

                    common.set_input(interpreter, pil_im)
                    interpreter.invoke()
                    objs = get_output(interpreter, score_threshold=args.threshold, top_k=args.top_k)
                    height, width, channels = cv2_im.shape

                    visitations.update(objs, cv2_im, labels)

                    cv2.namedWindow('Leroy', cv2.WINDOW_NORMAL)
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

                raw_capture.truncate(0)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            cv2.destroyAllWindows()

    except:
        logging.exception('Failed on the main program.')

if __name__ == '__main__':
    main()
