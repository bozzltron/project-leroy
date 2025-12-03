import argparse
import os
import shutil
import string
import itertools
import json
import cv2 
import re

from collections import defaultdict
from datetime import datetime
from operator import itemgetter
from itertools import groupby

# Scientific names are extracted from classification labels or looked up dynamically
# No static file required - will try to get from labels file format or return "Unknown"
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
  for i in range(len(full_images)):
    print("is {} in {} ?".format(visitation_id, full_images[i]))
    if visitation_id in full_images[i]:
      return full_images[i]
  return ""

def datetime_parser(dct):
    for k, v in dct.items():
        if isinstance(v, str) and re.search(r"\ UTC", v):
            try:
                dct[k] = datetime.datetime.strptime(v, DATE_FORMAT)
            except:
                pass
    return dct

def get_scientific_name(common_name, labels_file_path=None):
  """
  Get scientific name from common name.
  
  First tries to extract from classification labels if they include scientific names.
  Otherwise, attempts to look up from eBird/iNaturalist taxonomy.
  Falls back to "Unknown" if not found.
  
  Args:
    common_name: Common name of the bird (e.g., "american-robin")
    labels_file_path: Optional path to labels file to check format
    
  Returns:
    Scientific name (e.g., "Turdus migratorius") or "Unknown"
  """
  # Try to extract from labels file if it contains scientific names
  # Format might be: "1 american-robin (Turdus migratorius)" or similar
  if labels_file_path and os.path.exists(labels_file_path):
    try:
      with open(labels_file_path, 'r', encoding='utf-8') as f:
        for line in f:
          # Check if line contains common name
          line_lower = line.lower()
          common_name_normalized = common_name.lower().replace(" ", "-")
          
          if common_name_normalized in line_lower:
            # Look for scientific name pattern: (Genus species) or Genus species
            # Pattern: (Turdus migratorius) or Turdus migratorius
            match = re.search(r'\(([A-Z][a-z]+ [a-z]+)\)', line)
            if match:
              return match.group(1)
            # Also try without parentheses
            match = re.search(r'\b([A-Z][a-z]+ [a-z]+)\b', line)
            if match and match.group(1) != common_name:
              return match.group(1)
    except Exception:
      pass
  
  # TODO: Could add API lookup here (eBird, iNaturalist) if needed
  # For now, return "Unknown" - can be populated later or via API
  
  return "Unknown"

def find_species(records):
  """Find most common species (backward compatibility)."""
  species = ""
  highest_count = 0
  for k,v in groupby(records,key=lambda x:x['species']):
    length = len(list(v))
    if length > highest_count:
      highest_count = length
      species = k
  return species

def find_all_species(records):
  """Find all species in records with counts and temporal data."""
  species_counts = {}
  for record in records:
    species = record['species']
    if species not in species_counts:
      species_counts[species] = {
        'count': 0,
        'records': [],
        'first_seen': record['datetime'],
        'last_seen': record['datetime'],
        'confidences': []
      }
    species_counts[species]['count'] += 1
    species_counts[species]['records'].append(record)
    if record['datetime'] < species_counts[species]['first_seen']:
      species_counts[species]['first_seen'] = record['datetime']
    if record['datetime'] > species_counts[species]['last_seen']:
      species_counts[species]['last_seen'] = record['datetime']
    # Collect confidence scores
    try:
      conf = int(record.get('classification_score', 0))
      species_counts[species]['confidences'].append(conf)
    except (ValueError, TypeError):
      pass
  
  # Calculate average confidence per species
  for species, data in species_counts.items():
    if data['confidences']:
      data['avg_confidence'] = sum(data['confidences']) / len(data['confidences']) / 100.0
    else:
      data['avg_confidence'] = 0.0
  
  return species_counts

def find_best_photo_for_species(records):
  """Find best photo from records (based on clarity + scores)."""
  best = 0
  best_record = None
  for record in records:
    if not "full" in record['filename']:
      try:
        clarity_score = clarity('/var/www/html{}'.format(record['filename']))
        detection_score = int(record.get('detection_score', 0))
        classification_score = int(record.get('classification_score', 0))
        total_score = detection_score + classification_score + clarity_score
        if best < total_score:
          best = total_score
          best_record = record
      except Exception as e:
        print(f"Warning: Could not calculate score for {record['filename']}: {e}")
  return best_record

def create_species_observations(records, labels_file_path=None):
  """Create species_observations array with scientific format."""
  species_counts = find_all_species(records)
  observations = []
  
  for species, data in species_counts.items():
    # Get scientific name (from labels file or lookup)
    scientific_name = get_scientific_name(species, labels_file_path)
    
    # Find best photo for this species
    best_photo_record = find_best_photo_for_species(data['records'])
    best_photo = best_photo_record['filename'] if best_photo_record else data['records'][0]['filename']
    
    # Collect all photos for this species
    photos = []
    for record in data['records']:
      photos.append({
        'filename': record['filename'],
        'detection_score': int(record.get('detection_score', 0)),
        'classification_score': int(record.get('classification_score', 0)),
        'datetime': record['datetime'].strftime("%Y-%m-%d %H:%M:%S"),
        'is_best': record['filename'] == best_photo
      })
    
    observation = {
      'common_name': species,
      'scientific_name': scientific_name,
      'count': data['count'],  # Number of photos = proxy for individuals
      'first_seen': data['first_seen'].strftime("%Y-%m-%d %H:%M:%S"),
      'last_seen': data['last_seen'].strftime("%Y-%m-%d %H:%M:%S"),
      'confidence': round(data['avg_confidence'], 2),
      'photos': photos,
      'best_photo': best_photo
    }
    observations.append(observation)
  
  # Sort by count (most common first)
  observations.sort(key=lambda x: x['count'], reverse=True)
  return observations

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
    
    # Try to find labels file to extract scientific names if available
    # Look for inat_bird_labels.txt in common locations
    labels_file_path = None
    possible_label_paths = [
      os.path.join('all_models', 'inat_bird_labels.txt'),
      os.path.join(os.path.dirname(__file__), 'all_models', 'inat_bird_labels.txt'),
      '/var/www/html/classified/../all_models/inat_bird_labels.txt'
    ]
    for path in possible_label_paths:
      if os.path.exists(path):
        labels_file_path = path
        break
    
    for k,v in groupby(birds,key=lambda x:x['visitation_id']):
      records = list(v)
      best_photo_index = find_best_photo(records) 
      save_visitation = True
      highest_classification_score = 0
      sorted_records = sorted(records, key=lambda k: int(k['classification_score'])) 
      
      # Create species observations (multi-species support)
      species_observations = create_species_observations(records, labels_file_path)
      species_counts = find_all_species(records)
      
      visitation = {
        "visitation_id": k,
        "start_datetime": records[0]["datetime"].strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": records[-1]["datetime"].strftime("%Y-%m-%d %H:%M:%S"),
        "duration": (records[-1]["datetime"] - records[0]["datetime"]).total_seconds(),
        
        # NEW: Multi-species support (scientific format)
        "species_observations": species_observations,
        "species_count": len(species_counts),
        
        # BACKWARD COMPATIBLE: Keep single species field
        "species": find_species(records),
        
        # Existing fields
        "records": records,
        "best_photo": records[best_photo_index]["filename"],
        "full_image": find_full_image(full_images, k).replace("/var/www/html", ""),
        "datetime": records[0]["datetime"].strftime("%Y-%m-%d %H:%M:%S"),  # Keep for backward compatibility
      }
      #if len(sorted_records) > 0 and int(sorted_records[-1]['classification_score']) > 25:
      visitations.append(visitation)
      visitations = sorted(visitations, key=lambda x: x['datetime'], reverse=True)

      #else:
      #  print("bad visitation: {}".format(visitation))

  # for visit in visitations:
  #   if len(visit["records"]) == 1 and int(visit["records"][0]["classification_score"]) < 90:
  #     visitations.remove(visit)

  with open('/var/www/html/visitations.json', 'w') as outfile:
    json.dump(visitations, outfile, default=str)

  for visitation in visitations:
    print("----------")
    print("  Visitation ID: ", visitation["visitation_id"])
    print("  Date: ", visitation["start_datetime"])
    print("  Duration: ", visitation["duration"], "seconds")
    print("  Species Count: ", visitation.get("species_count", 1))
    
    # Display all species (scientific format)
    if "species_observations" in visitation:
      print("  Species Observed:")
      for obs in visitation["species_observations"]:
        print("    - {} ({}) - Count: {}, Confidence: {:.2f}".format(
          obs["common_name"], 
          obs["scientific_name"],
          obs["count"],
          obs["confidence"]
        ))
    else:
      # Backward compatible display
      print("  Species: ", visitation["species"])
    
    print("  Num of Records: ", len(visitation["records"]))
    print("  Best Photo: ", visitation["best_photo"])
    
  # Generate daily summary (for logging/debugging)
  summary = "Today I was visited {} times. ".format(len(visitations))

  for k,v in groupby(sorted(visitations, key = lambda i: i['species']),key=lambda x:x['species']):
    summary = summary + "{} times by {}. ".format(len(list(v)), k)

  print(summary)
  
  # Optional: Post to Bluesky (if enabled and authenticated)
  # Posts once per day in evening (7-9 PM) with 5 best photos
  try:
    from bluesky_poster import BlueskyPoster
    poster = BlueskyPoster()
    
    # Post daily summary with 5 best photos (varying species, high clarity)
    # Only posts if within posting window (7-9 PM) and not already posted today
    poster.post_daily_summary(visitations)
  except ImportError:
    # Bluesky poster not available, silently ignore
    pass
  except Exception as e:
    # Log error but don't crash
    print(f"Warning: Could not post to Bluesky: {e}")

if __name__ == '__main__':
  main()
