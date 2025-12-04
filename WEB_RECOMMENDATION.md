# Web App Framework Recommendation

## Current State
- React 16.13.1 + Material-UI v4
- Requires npm build process
- Heavy dependencies (~100MB+ node_modules)
- Overkill for simple data display

## Recommendation: **Vanilla JavaScript**

For a Raspberry Pi displaying visitations, vanilla JS is perfect:

### Advantages
✅ **Zero build step** - Just HTML/CSS/JS files
✅ **No dependencies** - No npm install needed
✅ **Lightweight** - ~50KB total vs 100MB+ node_modules
✅ **Fast** - No framework overhead
✅ **Simple** - Easy to maintain and modify
✅ **Works everywhere** - No compatibility issues
✅ **Real-time ready** - Just fetch JSON and update DOM

### What We Need
1. **Display visitations** - Grid/list of cards
2. **Show photos** - Image gallery
3. **Multi-species support** - Show all species per visitation
4. **Real-time updates** - Auto-refresh every 60s
5. **iNaturalist integration** - Submit button (future)

### Proposed Structure

```
web/
├── index.html          # Main page
├── styles.css          # All styles
├── app.js              # All JavaScript
└── assets/             # Images, icons (if needed)
```

### Technology Stack
- **HTML5** - Semantic markup
- **CSS3** - Modern CSS Grid/Flexbox (no framework needed)
- **Vanilla JavaScript (ES6+)** - Fetch API, template literals
- **Optional**: Tailwind CSS CDN (if we want utility classes, but not required)

### Features
- Responsive design (mobile-friendly)
- Auto-refresh visitations.json
- Modal for photo gallery
- Multi-species display with scientific names
- Clean, modern UI
- ~200 lines of code total

### Comparison

| Approach | Size | Build | Dependencies | Complexity |
|----------|------|-------|--------------|------------|
| **Vanilla JS** | ~50KB | None | 0 | Low ✅ |
| React + MUI | ~2MB | Required | 100+ | High |
| Alpine.js | ~15KB | None | 1 | Low |
| Preact | ~3KB | Optional | 1 | Medium |

**Recommendation: Vanilla JavaScript** - Perfect for this use case.

