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
r"""A demo using `ClassificationEngine` to classify an image.

You can run this example with the following command, which uses a
MobileNet model trained with the iNaturalist birds dataset, so it's
great at identifying different types of birds.

python3 classify_image.py \
--model models/mobilenet_v2_1.0_224_inat_bird_quant_edgetpu.tflite \
--label models/inat_bird_labels.txt \
--image images/parrot.jpg
"""

import argparse
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter
from pycoral.adapters import common
from pycoral.adapters.classify import get_classes
from PIL import Image
import os
import shutil
import string

def get_new_dir(dirpath):
  new_dir = ""
  path_sections = dirpath.split("/")
  if len(path_sections) == 4:
    date = path_sections[2]
    visitation_id = path_sections[3]
    new_dir = "/var/www/html/classified/{}/{}".format(date, visitation_id)
  return new_dir

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--model', help='File path of Tflite model.', default=os.path.join('all_models','mobilenet_v2_1.0_224_inat_bird_quant_edgetpu.tflite'))
  parser.add_argument('--label', help='File path of label file.', default=os.path.join('all_models','inat_bird_labels.txt'))
  parser.add_argument(
      '--image', help='File path of the image to be recognized.', required=False)
  parser.add_argument(
      '--dir', help='File path of the dir to be recognized.', required=False)
  parser.add_argument(
      '--dryrun', help='Whether to actually move files or not.', required=False, default=False)
  parser.add_argument('--top_k', type=int, default=3,
                        help='number of classes with highest score to display')
  parser.add_argument('--threshold', type=float, default=0.1,
                        help='class score threshold') 
  args = parser.parse_args()

  interpreter = make_interpreter(args.model)
  interpreter.allocate_tensors()
  # Prepare labels.
  labels = read_label_file(args.label)
  # Initialize engine.
  
  input_tensor_shape = interpreter.get_input_details()[0]['shape']
  if (input_tensor_shape.size != 4 or input_tensor_shape[0] != 1):
    raise RuntimeError('Invalid input tensor shape! Expected: [1, height, width, channel]')

  output_tensors = len(interpreter.get_output_details())
  if output_tensors != 1:
    raise ValueError(
            ('Classification model should have 1 output tensor only!'
             'This model has {}.'.format(output_tensors)))

  # Run inference.
  if args.image:
    img = Image.open(args.image)
    common.set_resized_input(interpreter, image.size, lambda size: image.resize(size, Image.NEAREST))
    interpreter.invoke()
    results = get_classes(interpreter, args.top_k, args.threshold)
    for result in results:
      print('---------------------------')
      print(labels[result[0]])
      print('Score : ', result[1])
  if args.dir:
    f = []
    for (dirpath, dirnames, filenames) in os.walk(args.dir):
          for filename in filenames:
            try:
              filepath = "{}/{}".format(dirpath,filename)
              if "boxed" in filename:
                print("attempting to classify {}".format(filepath))
                img = Image.open(filepath)
                common.set_resized_input(interpreter, img.size, lambda size: img.resize(size, Image.NEAREST))
                interpreter.invoke()
                results = get_classes(interpreter, args.top_k, args.threshold)
                for result in results:
                  label = labels[result[0]]
                  percent = int(100 * result[1])
                  if label != "background":
                    print('dirpath', dirpath)
                    path_sections = dirpath.split("/")
                    new_dir = "/var/www/html/classified/"
                    if len(path_sections) == 4:
                      date = path_sections[2]
                      visitation_id = path_sections[3]
                      new_dir = "/var/www/html/classified/{}/{}".format(date, visitation_id)
                    newname = filename.replace(".png", "_{}_{}.png".format(label.replace(" ", "-"), percent))
                    newpath = "{}/{}".format(new_dir, newname)
                    print('move {} -> {}'.format(filepath, newpath))
                    print('dryrun', args.dryrun)
                    if args.dryrun == False:
                      if not os.path.exists(new_dir):
                        os.makedirs(new_dir)
                      shutil.move(os.path.abspath(filepath), os.path.abspath(newpath))
              if "full" in filename:
                new_dir = get_new_dir(dirpath)
                print('new full image dir {}'.format(new_dir))
                new_path = "{}/{}".format(new_dir, filename)
                if os.path.exists(new_dir):
                  print('full image move {} -> {}'.format(os.path.abspath(filepath), os.path.abspath(new_path)))
                  if args.dryrun == False:
                    shutil.move(os.path.abspath(filepath), os.path.abspath(new_path))
                else:
                  print('full image new directory doesnt exist')
            except Exception as e:
                print("failed to classify {}".format(e))

if __name__ == '__main__':
  main()
