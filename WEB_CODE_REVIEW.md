# Web App Code Review

## Current State

The web app is a React application using Material-UI v4 that displays bird visitations in real-time.

## Issues Found

### 1. **Hardcoded IP Addresses** 🔴 Critical
- `App.jsx`: Hardcoded `192.168.86.47`
- `BirdCard.jsx`: Hardcoded `192.168.86.53`
- `Slideshow.jsx`: Hardcoded `192.168.86.53`
- **Impact**: Breaks when IP changes, not portable
- **Fix**: Use relative paths or environment variables

### 2. **Single Species Display** 🔴 Critical
- Only displays `visit.species` (single species)
- Doesn't show `species_observations` array (multi-species support)
- Doesn't display scientific names
- **Impact**: Doesn't match new data model with multi-species visitations
- **Fix**: Update to display all species in a visitation

### 3. **Outdated Dependencies** 🟡 Medium
- Material-UI v4 (latest is v5/MUI)
- React 16.13.1 (latest is 18+)
- **Impact**: Security vulnerabilities, missing features
- **Fix**: Update to latest versions or migrate to MUI

### 4. **Missing Error Handling** 🟡 Medium
- No error display in UI
- No loading states
- No empty state handling
- **Impact**: Poor user experience
- **Fix**: Add error boundaries, loading spinners, empty states

### 5. **Missing Features** 🟢 Low
- No iNaturalist integration
- No way to export/submit observations
- No filtering or search
- **Impact**: Limited functionality
- **Fix**: Add iNaturalist API integration

### 6. **Code Quality** 🟡 Medium
- Duplicate key prop in BirdCard.jsx (line 105)
- Inconsistent path handling
- No TypeScript for type safety
- **Impact**: Potential bugs, harder to maintain
- **Fix**: Add TypeScript, fix linting issues

## New Data Model

The visitation data now includes:

```json
{
  "visitation_id": "uuid",
  "start_datetime": "2024-01-15 10:30:00",
  "end_datetime": "2024-01-15 10:45:00",
  "duration": 900,
  "species_count": 2,
  "species": "American Robin",  // Backward compatible
  "species_observations": [
    {
      "common_name": "American Robin",
      "scientific_name": "Turdus migratorius",
      "count": 4,
      "first_seen": "2024-01-15 10:30:15",
      "last_seen": "2024-01-15 10:44:30",
      "confidence": 0.92,
      "photos": [...],
      "best_photo": "..."
    },
    {
      "common_name": "House Finch",
      "scientific_name": "Haemorhous mexicanus",
      "count": 2,
      ...
    }
  ],
  "best_photo": "...",
  "full_image": "...",
  "records": [...]  // Backward compatible
}
```

## Recommendations

### Priority 1: Fix Multi-Species Display
- Update `BirdCard.jsx` to show all species in a visitation
- Display scientific names
- Show species count badge
- Group photos by species

### Priority 2: Remove Hardcoded IPs
- Use relative paths (works on same host)
- Or use environment variables for API base URL

### Priority 3: Add iNaturalist Integration
- Research pyinaturalist library
- Add "Submit to iNaturalist" button
- Map visitation data to iNaturalist observation format
- Handle OAuth authentication

### Priority 4: Improve UX
- Add loading states
- Add error handling
- Add empty states
- Add filtering/search

### Priority 5: Update Dependencies
- Migrate to MUI v5
- Update React to latest
- Consider TypeScript migration

