import argparse
import os
import shutil
import string
from collections import defaultdict
from datetime import datetime
import itertools
from operator import itemgetter
import json

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
      "records": []
    }

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--dir', help='File path of the dir to be recognized.', required=True)
  args = parser.parse_args()

  visitations = []
  for (dirpath, dirnames, filenames) in os.walk(args.dir):
    # filter to just boxed names
    filtered = filter(only_boxed, filenames)
    parsed = map(parse, filtered)
    birds = sorted(parsed, key=itemgetter('datetime'))
    current_visitation = initialize_visitation()
    for bird in birds:

      if not current_visitation["species"]:
        current_visitation["species"] = bird["species"]

      #time_diff = target["datetime"] - bird["datetime"]
      if current_visitation["species"] == bird["species"]:
        current_visitation["records"].append(bird)
      else:
        if len(current_visitation["records"]) > 0:
            if len(current_visitation["records"]) > 1:
              current_visitation["duration"] = (current_visitation["records"][-1]["datetime"] - current_visitation["records"][0]["datetime"]).total_seconds()
            visitations.append(current_visitation)
            current_visitation = initialize_visitation()
  
    #with open('visitations.json', 'w') as outfile:
    #  json.dump(visitations, outfile)

    print(len(visitations), " visitations")
    for visitation in visitations:
      print("----------")
      print("  Species: ", visitation["species"])
      print("  Date: ", visitation["records"][0]["datetime"])
      print("  Duration: ", visitation["duration"])
      print("  Num of Records: ", len(visitation["records"]))
      print("  Classification Scores: ", list(map(lambda x : x["classification_score"], visitation["records"])))


if __name__ == '__main__':
  main()
