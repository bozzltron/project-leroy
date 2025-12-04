# Project Leroy - Code Review & Consolidation Analysis

## ✅ COMPLETED CLEANUP

All major cleanup tasks have been completed:
- ✅ Created `utils.py` and consolidated duplicate functions
- ✅ Removed old React web app files
- ✅ Removed unused scripts and commented code
- ✅ Removed outdated documentation
- ✅ Cleaned up Makefile (removed obsolete Docker targets)
- ✅ Removed unused imports and fixed function signatures
- ✅ Removed video recording code (can be re-added later)

## Executive Summary

This document identifies unnecessary code, duplication, and opportunities for consolidation to improve maintainability and reduce complexity.

---

## 🔴 Critical Issues - Code Duplication

### 1. Duplicate `load_labels()` Function
**Location**: `leroy.py:40-54` and `classify.py:23-38`

**Problem**: Identical function in two files
```python
# Both files have:
def load_labels(path):
    """Load label file and return as dictionary."""
    p = re.compile(r'\s*(\d+)(.+)')
    labels = {}
    # ... identical code ...
```

**Solution**: Create `utils.py` and move shared functions there
- Create `utils.py` with `load_labels()`
- Import from `utils` in both files

**Impact**: Reduces duplication, single source of truth

---

### 2. Duplicate `clarity()` Function
**Location**: `photo.py:13-17` and `visitation.py:20-25`

**Problem**: Same function in two places
```python
# photo.py
def clarity(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return 0 if image is None else cv2.Laplacian(gray, cv2.CV_64F).var()

# visitation.py
def clarity(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return 0 if image is None else cv2.Laplacian(gray, cv2.CV_64F).var()
```

**Note**: `visitation.py` version takes a path, `photo.py` takes an image array

**Solution**: 
- Consolidate into `utils.py` with both variants:
  - `clarity_from_image(image: np.ndarray)` 
  - `clarity_from_path(image_path: str)`
- Or standardize on one approach

**Impact**: Removes duplication, consistent clarity calculation

---

## 🟡 Unused/Dead Code

### 3. Old React Web App Files
**Location**: `web/src/`, `web/build/`, `web/node_modules/`, `web/package.json`, `web/package-lock.json`

**Problem**: Old React app is no longer used (replaced with vanilla JS)

**Files to Remove**:
- `web/src/` (entire directory)
- `web/build/` (entire directory)
- `web/node_modules/` (entire directory)
- `web/package.json`
- `web/package-lock.json`
- `web/public/` (if not needed)

**Solution**: Delete these directories/files

**Impact**: Reduces repository size, eliminates confusion

---

### 4. Unused Scripts
**Location**: `encode.sh`

**Problem**: Script exists but is never referenced
- Not called by any other script
- Not mentioned in README
- Not used in Makefile

**Solution**: Remove if not needed, or document its purpose

**Impact**: Cleaner codebase

---

### 5. Commented-Out Code in `run.sh`
**Location**: `run.sh:56-58`

**Problem**: Old Docker commands commented out
```bash
#python3 two_models.py
#docker run --privileged --device /dev/video0 ...
#docker run michaelbosworth/project-leroy:latest two_models.py
```

**Solution**: Remove commented-out code (Git history preserves it)

**Impact**: Cleaner, less confusing

---

### 6. Unused Function in `photo.py`
**Location**: `photo.py:19-20`

**Problem**: `is_focused()` has `self` parameter but isn't a method
```python
def is_focused(self, image):  # 'self' not needed
    return clarity(image) > 100
```

**Solution**: Remove `self` parameter or remove function if unused

**Impact**: Fixes incorrect signature

---

### 7. Unused Import in `visitations.py`
**Location**: `visitations.py:8`

**Problem**: `from imutils.video import VideoStream` - not used anywhere in file

**Solution**: Remove unused import

**Impact**: Cleaner imports

---

## 🟠 Documentation Files to Consolidate

### 8. Redundant Documentation
**Files**:
- `WEB_CODE_REVIEW.md` - Review of old React app (no longer relevant)
- `WEB_RECOMMENDATION.md` - Recommendation to switch to vanilla JS (already done)
- `DIRECTORY_MANAGEMENT.md` - Could be in README
- `INATURALIST_INTEGRATION.md` - Future feature (keep or archive)

**Solution**: 
- Delete `WEB_CODE_REVIEW.md` and `WEB_RECOMMENDATION.md` (outdated)
- Move `DIRECTORY_MANAGEMENT.md` content to README
- Keep `INATURALIST_INTEGRATION.md` if planning to implement

**Impact**: Less documentation clutter

---

## 🔵 Code Organization Issues

### 9. `visitation.py` vs `visitations.py` - Naming Confusion
**Current State**:
- `visitations.py` - Real-time visitation tracking (used by `leroy.py`)
- `visitation.py` - Post-processing visitation analysis (used by `classify.sh`)

**Problem**: Similar names cause confusion

**Solution**: Consider renaming for clarity:
- `visitations.py` → `visitation_tracker.py` (real-time tracking)
- `visitation.py` → `visitation_processor.py` (post-processing)

**Impact**: Clearer purpose, less confusion

---

### 10. Missing `utils.py` for Shared Functions
**Problem**: No central place for shared utilities

**Functions to Move to `utils.py`**:
- `load_labels()` (from `leroy.py` and `classify.py`)
- `clarity()` variants (from `photo.py` and `visitation.py`)
- `has_disk_space()` (from `photo.py` - could be shared)
- `add_padding_to_bbox()` (from `visitations.py` - used by `leroy.py`)

**Solution**: Create `utils.py` and consolidate shared functions

**Impact**: Better code organization, DRY principle

---

### 11. `retrain_model.py` - Future Feature
**Location**: `retrain_model.py`

**Problem**: Script exists but not currently used in workflow

**Solution**: 
- Keep if planning to use soon
- Or move to `scripts/` or `future/` directory
- Or remove if not needed

**Impact**: Clearer what's active vs future

---

## 🟢 Makefile Cleanup

### 12. Obsolete Makefile Targets
**Location**: `Makefile`

**Obsolete Targets** (old Docker setup):
- `build`, `push` (old Docker image)
- `run`, `run_continuous`, `run_on_mac` (old Docker commands)
- `start_machine`, `change_docker_env`, `restore_docker_env` (Docker Machine - obsolete)
- `classify`, `generate_daily_report` (old Docker commands)
- `sync_from_pi`, `sync_to_pi` (old sync commands)
- `mp4_to_gif`, `mp4_to_h264` (video encoding - not used)
- `set_resolution` (old camera setup)

**Solution**: Remove obsolete targets or move to `Makefile.legacy`

**Impact**: Cleaner Makefile, only relevant commands

---

## 📊 Summary Statistics

### Files to Remove:
1. `web/src/` (old React app)
2. `web/build/` (old React build)
3. `web/node_modules/` (old React dependencies)
4. `web/package.json` (old React)
5. `web/package-lock.json` (old React)
6. `web/public/` (if not needed)
7. `encode.sh` (unused)
8. `WEB_CODE_REVIEW.md` (outdated)
9. `WEB_RECOMMENDATION.md` (outdated)

### Files to Create:
1. `utils.py` (shared utilities)

### Files to Consolidate:
1. Move `load_labels()` to `utils.py`
2. Move `clarity()` to `utils.py`
3. Move `add_padding_to_bbox()` to `utils.py` (or keep in `visitations.py` if only used there)

### Code to Clean:
1. Remove commented-out code in `run.sh`
2. Fix `is_focused()` in `photo.py`
3. Remove unused imports
4. Clean up Makefile

---

## 🎯 Recommended Action Plan

### Phase 1: Quick Wins (Low Risk)
1. ✅ Remove old React web app files
2. ✅ Remove commented-out code in `run.sh`
3. ✅ Remove unused `encode.sh`
4. ✅ Remove outdated documentation files
5. ✅ Fix `is_focused()` signature
6. ✅ Remove unused imports

### Phase 2: Consolidation (Medium Risk)
1. ✅ Create `utils.py`
2. ✅ Move `load_labels()` to `utils.py`
3. ✅ Move `clarity()` to `utils.py`
4. ✅ Update imports in `leroy.py`, `classify.py`, `photo.py`, `visitation.py`

### Phase 3: Refactoring (Higher Risk)
1. ⚠️ Consider renaming `visitations.py` → `visitation_tracker.py`
2. ⚠️ Consider renaming `visitation.py` → `visitation_processor.py`
3. ⚠️ Clean up Makefile (remove obsolete targets)

---

## 📝 Notes

- **`retrain_model.py`**: Keep for now if active learning is planned
- **`bluesky_poster.py`**: Keep (optional feature, used by `visitation.py`)
- **`camera_manager.py`**: Keep (used by `leroy.py`)
- **`hailo_inference.py`**: Keep (core AI functionality)
- **`active_learning.py`**: Keep (used by `leroy.py` and `classify.py`)

