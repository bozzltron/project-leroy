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

def classification_scores(bird):
  return bird["classification_score"]

def parse(filename):
  data = filename.split('_')
  return {
    "filename": filename,
    "datetime": datetime.strptime("{} {}".format(data[1], data[2]), '%Y-%m-%d %H-%M-%S'),
    "detection_score": data[3],
    "species": data[4].replace("-", " "),
    "classification_score": data[5].replace(".png", "")
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
    total_score = int(record["classification_score"]) + int(record["detection_score"])
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
    current_visitation = initialize_visitation()
    for bird in birds:
      valid = True
      if current_visitation["species"] != bird["species"]:
        if len(current_visitation["records"]) > 0:
          if len(current_visitation["records"]) > 1:
            best_photo_index = find_best_photo(current_visitation["records"]) 
            current_visitation["best_photo"] = current_visitation["records"][best_photo_index]["filename"]
            current_visitation["duration"] = (current_visitation["records"][-1]["datetime"] - current_visitation["records"][0]["datetime"]).total_seconds()
          if len(current_visitation["records"]) == 1 and int(current_visitation["records"][0]["classification_score"]) < 50:
            bad_visitation = current_visitation["records"][0]
            print("detected poor visitation", bad_visitation["species"], bad_visitation["classification_score"])
            valid = False
          if valid:
            visitations.append(current_visitation)
          current_visitation = initialize_visitation()
        current_visitation["species"] = bird["species"]
      current_visitation["records"].append(bird)

    # # find visitations that need merged
    # lists_to_join = []
    # for idx, visit in enumerate(visitations):
    #   lookahead = visitations[idx+1] if idx < len(visitations) else None
    #   if lookahead and (visit["species"] == lookahead["species"]):
    #     diff = lookahead["records"][0]["datetime"] - visit["records"][-1]["datetime"]
    #     if diff.total_seconds < 60:
    #       lists_to_join.append([idx, idx + 1])

    # # merge them
    # for indexes in lists_to_join:
    #   destination = visitations[indexes[0]]
    #   source = visitations[indexes[1]]
    #   destination['records'] = destination["records"] + source["records"]
    1
    # # clean up
    # for indexes in lists_to_join:
    #   visitations.remove(indexes[1])  

    print(len(visitations), " visitations")
    for visitation in visitations:
      print("----------")
      print("  Species: ", visitation["species"])
      print("  Date: ", visitation["records"][0]["datetime"])
      print("  Duration: ", visitation["duration"])
      print("  Num of Records: ", len(visitation["records"]))
      print("  Classification Scores: ", list(map(lambda x : x["classification_score"], visitation["records"])))
      print("  Best Photo: ", visitation["best_photo"])
    
  with open('visitations.json', 'w') as outfile:
     json.dump(visitations, outfile, default=str)

    # groups = []
    # uniquekeys = []
    # for k, g in groupby(visitations, key=lambda x:x['species']):
    #     groups.append(list(g))      # Store group iterator as a list
    #     uniquekeys.append(k)
    # print("groups")
    # print(groups)

if __name__ == '__main__':
  main()
