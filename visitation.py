import argparse
import os
import shutil
import string
from collections import defaultdict
from datetime import datetime
import itertools
from operator import itemgetter
import json
from itertools import groupby
import cv2 

def classification_scores(bird):
  return bird["classification_score"]

def clarity(image_path):
	# compute the Laplacian of the image and then return the focus
	# measure, which is simply the variance of the Laplacian
  image = cv2.imread("storage/classified/{}".format(image_path))
  gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
  return 0 if image is None else cv2.Laplacian(gray, cv2.CV_64F).var()

def parse(filename):
  data = filename.split('_')
  return {
    "filename": filename,
    "datetime": datetime.strptime("{} {}".format(data[1], data[2]), '%Y-%m-%d %H-%M-%S'),
    "detection_score": data[3],
    "visitation_id": "" if len(data) == 6 else data[4],
    "species": data[4].replace("-", " ") if len(data) == 6 else data[5].replace("-", " "),
    "classification_score": data[5].replace(".png", "") if len(data) == 6 else data[6].replace(".png", "")
  }

def only_boxed(name):  
    if ("boxed" in name): 
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
    clarity_score = clarity(record['filename'])
    total_score = int(record["classification_score"]) + int(record["detection_score"]) + clarity_score
    if best < total_score:
      best = total_score
      best_index = index
  return best_index

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
    # filter to just boxed names
    filtered = filter(only_boxed, filenames)
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
        "best_photo": records[best_photo_index]["filename"]
      }
      if len(sorted_records) > 0 and int(sorted_records[-1]['classification_score']) > 30:
        visitations.append(visitation)
      else:
        print("bad visitation: {}".format(visitation))

  for visit in visitations:
    if len(visit["records"]) == 1 and int(visit["records"][0]["classification_score"]) < 90:
      visitations.remove(visit)

  with open('visitations.json', 'w') as outfile:
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
