import argparse
import os
import shutil
import string
import itertools
import json
import cv2 

from collections import defaultdict
from datetime import datetime
from operator import itemgetter
from itertools import groupby
def classification_scores(bird):
  return bird["classification_score"]

def clarity(image_path):
	# compute the Laplacian of the image and then return the focus
	# measure, which is simply the variance of the Laplacian
  image = cv2.imread(image_path)
  gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
  return 0 if image is None else cv2.Laplacian(gray, cv2.CV_64F).var()

def parse(filename):
  path = filename.split('/')
  data = filename.split('_')
  if len(data) == 6:
    return {
      "filename": filename.replace('/var/www/html', ''),
      "datetime": datetime.strptime("{} {}".format(data[1], data[2]), '%Y-%m-%d %H-%M-%S'),
      "detection_score": data[3],
      "visitation_id": "",
      "species": data[4].replace("-", " "),
      "classification_score": data[5].replace(".png", "")
    }
  if len(data) == 7:  
    return {
      "filename": filename.replace('/var/www/html', ''),
      "datetime": datetime.strptime("{} {}".format(data[1], data[2]), '%Y-%m-%d %H-%M-%S'),
      "detection_score": data[3],
      "visitation_id": data[4],
      "species": data[5].replace("-", " "),
      "classification_score": data[6].replace(".png", "")
    }
  print('path'.format(path))
  return {
    "filename": filename.replace('/var/www/html', ''),
    "datetime": datetime.strptime("{} {}".format(data[1], data[2]), '%Y-%m-%d %H-%M-%S') if len(data) == 7 else datetime.strptime("{} {}".format(path[5], data[1]), '%Y-%m-%d %H-%M-%S'),
    "detection_score": data[2],
    "visitation_id": path[6],
    "species": data[3].replace("-", " "),
    "classification_score": data[4].replace(".png", "")
  }

def only_boxed(name):  
    if ("boxed" in name): 
        return True
    else: 
        return False

def only_full(name):  
    if ("full" in name): 
        return True
    else: 
        return False

def initialize_visitation():
  return {
      "species": "",
      "duration": 1,
      "records": [],
      "best_photo": ""
    }

def find_best_photo(records):
  best = 0
  best_index = 0
  for index, record in enumerate(records, start=0):
    if not "full" in record['filename']:
      clarity_score = clarity('/var/www/html{}'.format(record['filename']))
      total_score = int(record["classification_score"]) + int(record["detection_score"]) + clarity_score
      if best < total_score:
        best = total_score
        best_index = index
  return best_index

def find_full_image(full_images, visitation_id):
  index = -1
  for i in range(len(full_images)):
    if visitation_id in full_images[i]:
      index == i
  if index != -1:
    return full_images[i]
  else:
    return ""

def datetime_parser(dct):
    for k, v in dct.items():
        if isinstance(v, basestring) and re.search("\ UTC", v):
            try:
                dct[k] = datetime.datetime.strptime(v, DATE_FORMAT)
            except:
                pass
    return dct

def find_species(records):
  species = ""
  highest_count = 0
  for k,v in groupby(records,key=lambda x:x['species']):
    length = len(list(v))
    if length > highest_count:
      highest_count = length
      species = k
  return species

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--dir', help='File path of the dir to be recognized.', required=True)
  parser.add_argument(
      '--date', help='Calculate visitations for one day.', required=False)
  args = parser.parse_args()

  visitations = []
  for (dirpath, dirnames, filenames) in os.walk(args.dir):
    filepaths = []
    for filename in filenames:
        filepaths.append(os.path.join(dirpath, filename))

    # filter to just boxed names
    full_images = list(filter(only_full, filepaths))
    filtered = filter(only_boxed, filepaths)
    parsed = map(parse, filtered)

    if args.date:
        date = datetime.strptime(args.date, '%Y-%m-%d')
        parsed = filter(lambda x : x["datetime"].date() == date.date(), parsed)

    birds = sorted(parsed, key=itemgetter('datetime'))
    for k,v in groupby(birds,key=lambda x:x['visitation_id']):
      records = list(v)
      best_photo_index = find_best_photo(records) 
      save_visitation = True
      highest_classification_score = 0
      sorted_records = sorted(records, key=lambda k: int(k['classification_score'])) 
      visitation = {
        "visitation_id": k,
        "species": find_species(records),
        "duration": (records[-1]["datetime"] - records[0]["datetime"]).total_seconds(),
        "records": records,
        "best_photo": records[best_photo_index]["filename"],
        "full_image": find_full_image(full_images, k)
      }
      #if len(sorted_records) > 0 and int(sorted_records[-1]['classification_score']) > 25:
      visitations.append(visitation)
      #else:
      #  print("bad visitation: {}".format(visitation))

  # for visit in visitations:
  #   if len(visit["records"]) == 1 and int(visit["records"][0]["classification_score"]) < 90:
  #     visitations.remove(visit)

  with open('/var/www/html/visitations.json', 'w') as outfile:
    json.dump(visitations, outfile, default=str)

  for visitation in visitations:
    print("----------")
    print("  Species: ", visitation["species"])
    print("  Date: ", visitation["records"][0]["datetime"])
    print("  Duration: ", visitation["duration"])
    print("  Num of Records: ", len(visitation["records"]))
    print("  Classification Scores: ", list(map(lambda x : x["classification_score"], visitation["records"])))
    print("  Best Photo: ", visitation["best_photo"])
    
  tweet = "Today I was visited {} times. ".format(len(visitations))

  for k,v in groupby(sorted(visitations, key = lambda i: i['species']),key=lambda x:x['species']):
    tweet = tweet + "{} times by {}. ".format(len(list(v)), k)

  print(tweet)

if __name__ == '__main__':
  main()
