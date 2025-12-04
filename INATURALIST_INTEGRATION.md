# iNaturalist Integration Plan

## Overview

Project Leroy's visitation data format already matches iNaturalist's observation format, making integration straightforward.

## Data Format Compatibility

### Project Leroy Visitation Format
```json
{
  "visitation_id": "uuid",
  "start_datetime": "2024-01-15 10:30:00",
  "end_datetime": "2024-01-15 10:45:00",
  "duration": 900,
  "species_observations": [
    {
      "common_name": "American Robin",
      "scientific_name": "Turdus migratorius",
      "count": 4,
      "first_seen": "2024-01-15 10:30:15",
      "last_seen": "2024-01-15 10:44:30",
      "confidence": 0.92,
      "best_photo": "/classified/2024-01-15/uuid/boxed_...png",
      "photos": [...]
    }
  ],
  "best_photo": "...",
  "full_image": "..."
}
```

### iNaturalist Observation Format
```json
{
  "observation": {
    "species_guess": "Turdus migratorius",
    "observed_on_string": "2024-01-15 10:30:00",
    "time_zone": "America/New_York",
    "description": "Automated observation from Project Leroy",
    "tag_list": "project-leroy,automated",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "observation_photos_attributes": [
      {
        "photo": "<base64_encoded_image>"
      }
    ]
  }
}
```

## Mapping Strategy

### One Visitation → Multiple Observations

Since a visitation can contain multiple species, we should create **one observation per species**:

```python
def create_inaturalist_observations(visitation):
    """Convert Project Leroy visitation to iNaturalist observations."""
    observations = []
    
    for species_obs in visitation['species_observations']:
        observation = {
            'observation': {
                'species_guess': species_obs['scientific_name'],
                'observed_on_string': species_obs['first_seen'],
                'time_zone': get_timezone(),  # From system or config
                'description': f"Automated observation from Project Leroy. "
                              f"Confidence: {species_obs['confidence']:.0%}. "
                              f"Count: {species_obs['count']} individuals.",
                'tag_list': 'project-leroy,automated,bird-watching',
                'latitude': get_location_latitude(),  # From config
                'longitude': get_location_longitude(),  # From config
                'observation_photos_attributes': [
                    {
                        'photo': encode_image(photo_path)
                    }
                    for photo_path in species_obs['photos'][:5]  # Limit to 5 photos
                ]
            }
        }
        observations.append(observation)
    
    return observations
```

## Implementation Options

### Option 1: Python Script (Recommended)
Create `submit_to_inaturalist.py` that:
- Reads `visitations.json`
- Converts to iNaturalist format
- Uses `pyinaturalist` library
- Handles OAuth authentication
- Submits observations

**Pros**: 
- Can run as cron job
- Easy to test
- Can batch submit

**Cons**: 
- Requires Python dependency (`pyinaturalist`)

### Option 2: Web UI Button
Add "Submit to iNaturalist" button in web interface:
- User clicks button
- Opens OAuth flow
- Submits selected visitation

**Pros**: 
- User control
- Can review before submitting

**Cons**: 
- Requires user interaction
- More complex OAuth flow

### Option 3: Automatic Submission
Auto-submit visitations after classification:
- Modify `visitation.py` or `classify.sh`
- Submit after processing

**Pros**: 
- Fully automated
- No user interaction

**Cons**: 
- Need to handle errors
- May submit incorrect identifications

## Recommended Approach

**Hybrid**: Python script + Web UI

1. **Python Script** (`submit_to_inaturalist.py`):
   - Can be called manually or via cron
   - Handles bulk submissions
   - Good for initial setup/testing

2. **Web UI Button** (future):
   - Add "Submit to iNaturalist" button per visitation
   - User can review and submit
   - Better for quality control

## Required Setup

### 1. Install pyinaturalist
```bash
pip install pyinaturalist
```

### 2. Register iNaturalist App
1. Go to https://www.inaturalist.org/oauth/applications
2. Create new application
3. Get `client_id` and `client_secret`
4. Set redirect URI (if using web flow)

### 3. Authentication

**Option A: Personal Access Token** (Simplest for automated)
```python
from pyinaturalist import get_access_token

token = get_access_token(
    username='your_username',
    password='your_password',
    app_id='your_client_id',
    app_secret='your_client_secret'
)
```

**Option B: OAuth Flow** (Better for web UI)
- User authorizes via browser
- Get access token
- Store token securely

### 4. Configuration

Add to `.env` or config file:
```bash
INATURALIST_ENABLED=true
INATURALIST_CLIENT_ID=your_client_id
INATURALIST_CLIENT_SECRET=your_client_secret
INATURALIST_USERNAME=your_username
INATURALIST_PASSWORD=your_password  # Or use token
INATURALIST_LATITUDE=40.7128
INATURALIST_LONGITUDE=-74.0060
INATURALIST_TIMEZONE=America/New_York
```

## Implementation Steps

1. ✅ **Research** - Understand iNaturalist API (done)
2. ⏳ **Create Python script** - `submit_to_inaturalist.py`
3. ⏳ **Add configuration** - Environment variables
4. ⏳ **Test submission** - Manual testing
5. ⏳ **Add to workflow** - Optional cron job or manual trigger
6. ⏳ **Web UI button** - Future enhancement

## Code Example (Future)

```python
# submit_to_inaturalist.py
from pyinaturalist import create_observation, upload_photo
import json
import os
from pathlib import Path

def submit_visitation_to_inaturalist(visitation, config):
    """Submit a visitation to iNaturalist."""
    observations_created = []
    
    for species_obs in visitation.get('species_observations', []):
        # Create observation
        obs_data = {
            'species_guess': species_obs['scientific_name'],
            'observed_on_string': species_obs['first_seen'],
            'time_zone': config['timezone'],
            'latitude': config['latitude'],
            'longitude': config['longitude'],
            'description': f"Automated observation from Project Leroy. "
                          f"Confidence: {species_obs['confidence']:.0%}."
        }
        
        observation = create_observation(
            access_token=config['access_token'],
            **obs_data
        )
        
        # Upload photos
        for photo_path in species_obs['photos'][:5]:
            upload_photo(
                observation_id=observation['id'],
                photo_path=photo_path,
                access_token=config['access_token']
            )
        
        observations_created.append(observation)
    
    return observations_created
```

## Considerations

1. **Location**: Need to configure latitude/longitude for observations
2. **Quality Control**: Should review before submitting? Or auto-submit high-confidence?
3. **Rate Limits**: iNaturalist has rate limits - batch submissions carefully
4. **Photo Quality**: Only submit high-quality photos
5. **Privacy**: Consider if location should be obscured
6. **Taxon ID**: Can look up taxon_id from scientific name for better accuracy

## Next Steps

1. Create `submit_to_inaturalist.py` script
2. Add configuration options
3. Test with one visitation
4. Integrate into workflow (optional cron job)
5. Add web UI button (future)

