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
from edgetpu.classification.engine import ClassificationEngine
from edgetpu.utils import dataset_utils
from PIL import Image
import os
import shutil
import string

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
  args = parser.parse_args()


  # Prepare labels.
  labels = dataset_utils.read_label_file(args.label)
  # Initialize engine.
  engine = ClassificationEngine(args.model)
  
  # Run inference.
  if args.image:
    img = Image.open(args.image)
    for result in engine.classify_with_image(img, top_k=3):
      print('---------------------------')
      print(labels[result[0]])
      print('Score : ', result[1])
  if args.dir:
    f = []
    for (dirpath, dirnames, filenames) in os.walk(args.dir):
          for filename in filenames:
            try:
              if "boxed" in filename:
                filepath = "{}{}".format(dirpath,filename)
                print("attempting to classify {}".format(filepath))
                img = Image.open(filepath)
                for result in engine.classify_with_image(img, top_k=3):
                  label = labels[result[0]]
                  percent = int(100 * result[1])
                  if label != "background":
                    print('dirpath', dirpath)
                    path_sections = dirpath.split("/")
                    new_dir = "storage/classified/"
                    if len(path_sections) == 4:
                      date = path_sections[2]
                      visitation_id = path_sections[3]
                      new_dir = "storage/classified/{}/{}".format(date, visitation_id)
                    newname = filename.replace(".png", "_{}_{}.png".format(label.replace(" ", "-"), percent))
                    newpath = "{}/{}".format(new_dir, newname)
                    print('move {} -> {}'.format(filepath, newpath))
                    fullpath = filepath.replace("boxed", "full")
                    newfullpath = newpath.replace("boxed", "full")
                    print('move {} -> {}'.format(fullpath, newfullpath))
                    print('dryrun', args.dryrun)
                    if args.dryrun == False:
                      shutil.move(os.path.abspath(filepath), os.path.abspath(newpath))
                      shutil.move(os.path.abspath(fullpath), os.path.abspath(newfullpath))
            except:
                print("failed to classify ")

if __name__ == '__main__':
  main()
