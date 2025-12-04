# Directory Management - Automatic Creation

## Overview

All directories are **automatically created** when needed. No manual setup required!

## Automatic Directory Creation

### 1. Detection Phase (`leroy.py` → `photo.py`)

**Directory**: `storage/detected/{YYYY-MM-DD}/{visitation_id}/`

**Created by**: `photo.py::mkdirs()`
```python
def mkdirs(visitation_id):
    directory = "storage/detected/{}/{}".format(time.strftime("%Y-%m-%d"), visitation_id)
    if not os.path.exists(directory):
        os.makedirs(directory)  # Creates all parent directories automatically
    return directory
```

**When**: Automatically called when a bird is detected and photo needs to be saved.

**Files created**:
- `boxed_{HH-MM-SS}_{score}.png`
- `full_{HH-MM-SS}_{score}.png`

### 2. Classification Phase (`classify.py`)

**Directory**: `/var/www/html/classified/{YYYY-MM-DD}/{visitation_id}/`

**Created by**: `classify.py` (line 183)
```python
new_dir = "/var/www/html/classified/{}/{}".format(date, visitation_id)
os.makedirs(new_dir, exist_ok=True)  # Creates all parent directories automatically
```

**When**: Automatically called when moving classified images from `storage/detected/` to `/var/www/html/classified/`.

**Files moved**:
- `boxed_{timestamp}_{score}_{species}_{class_score}.png`
- `full_{timestamp}_{score}.png`

### 3. Active Learning (`active_learning.py`)

**Directories**: 
- `storage/active_learning/unknown_birds/`
- `storage/active_learning/non_birds/`
- `storage/active_learning/low_confidence/`
- `storage/active_learning/new_species_candidates/`

**Created by**: `ActiveLearningCollector.__init__()`
```python
for directory in [self.unknown_birds_dir, self.non_birds_dir, ...]:
    os.makedirs(directory, exist_ok=True)
```

**When**: Automatically created when `ActiveLearningCollector` is initialized (in `leroy.py` and `classify.py`).

### 4. Base Directories (Install Script)

**Created by**: `install-pi5.sh` (ensures base directories exist)

**Directories**:
- `storage/detected/` - Base for detection photos
- `storage/classified/` - Base for classified photos (optional)
- `storage/results/` - For logs
- `storage/active_learning/` - Base for active learning
- `/var/www/html/classified/` - Web-accessible classified images

**Note**: These are created during installation, but subdirectories are created automatically as needed.

## Summary

✅ **No manual directory creation needed**
✅ **All directories created automatically when first photo is saved**
✅ **Date-based organization happens automatically**
✅ **Visitation-based grouping happens automatically**

## Directory Structure (Auto-Generated)

```
storage/
└── detected/
    └── 2024-12-03/          # Created automatically on first photo of the day
        └── abc123-def456/   # Created automatically for each visitation
            ├── boxed_10-30-25_85.png
            └── full_10-30-20_85.png

/var/www/html/
└── classified/
    └── 2024-12-03/          # Created automatically by classify.py
        └── abc123-def456/   # Created automatically for each visitation
            ├── boxed_10-30-25_85_american-robin_92.png
            └── full_10-30-20_85.png
```

## Verification

To verify directories are being created:

```bash
# Check detection directories
ls -la storage/detected/

# Check classified directories
ls -la /var/www/html/classified/

# Watch for new directories being created
watch -n 1 'find storage/detected -type d | tail -10'
```

