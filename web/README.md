# Project Leroy Web Interface

Lightweight vanilla JavaScript web app for displaying bird visitations in real-time.

## Features

- ✅ **Multi-species support** - Displays all species in each visitation
- ✅ **Scientific names** - Shows both common and scientific names
- ✅ **Real-time updates** - Auto-refreshes every 60 seconds
- ✅ **Photo gallery** - Modal view with all photos
- ✅ **Responsive design** - Works on mobile and desktop
- ✅ **Zero dependencies** - No npm, no build step, just HTML/CSS/JS

## Structure

```
web/
├── index.html      # Main page
├── styles.css      # All styles
├── app.js          # All JavaScript
└── README.md       # This file
```

## Deployment

### On Raspberry Pi (Production)

**Nginx runs directly on the host** (not in Docker) for optimal performance. The `install-pi5.sh` script automatically:
- Installs nginx
- Copies web files to `/var/www/html/`
- Starts and enables nginx service

**Manual deployment** (if needed):
```bash
sudo cp index.html styles.css app.js /var/www/html/
```

### Local Development (Docker)

For local development/testing, use Docker to preview:
```bash
make web-preview
# Or: docker-compose -f docker-compose.nginx.yml up
```

**Note**: Docker is only for local development. On Raspberry Pi, nginx runs directly on the host.

## Usage

The app automatically:
1. Fetches `/visitations.json` on load
2. Displays visitations in a responsive grid
3. Auto-refreshes every 60 seconds
4. Shows multi-species information
5. Opens photo gallery modal on click

## Customization

- **Refresh interval**: Change `refreshInterval` in `app.js` (default: 60000ms)
- **Styling**: Edit `styles.css`
- **Layout**: Modify HTML structure in `index.html`

## iNaturalist Integration (Future)

See `INATURALIST_INTEGRATION.md` for planned integration.
