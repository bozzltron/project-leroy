#!/bin/bash
# Launch browser for Project Leroy web interface
# Only opens if browser is not already showing the web app
# 
# This script:
# 1. Waits for nginx to be ready
# 2. Checks if browser is already open
# 3. Only launches if browser is not already running
# 4. Uses app mode for a clean, fullscreen experience

set -e

# Load configuration from environment file if it exists
if [ -f "leroy.env" ]; then
    source leroy.env
fi

# Configuration (with defaults)
LEROY_WEB_PORT="${LEROY_WEB_PORT:-8080}"
LEROY_WEB_HOST="${LEROY_WEB_HOST:-localhost}"
LEROY_AUTO_LAUNCH_BROWSER="${LEROY_AUTO_LAUNCH_BROWSER:-true}"
BROWSER_CMD="${LEROY_BROWSER_CMD:-chromium-browser}"

WEB_URL="http://${LEROY_WEB_HOST}:${LEROY_WEB_PORT}"
CHECK_INTERVAL=5  # Check every 5 seconds
MAX_WAIT=30       # Wait up to 30 seconds for service to be ready

# Function to check if browser is already open to our URL
is_browser_open() {
    # Check if any browser process is running
    # We check for common browser processes and if they're accessing localhost
    if pgrep -f "chromium|chrome|firefox|epiphany" > /dev/null 2>&1; then
        # Check if any browser window is open to localhost
        # This is a best-effort check - we assume if browser is running, it might be our app
        # More sophisticated check would require checking actual window titles/URLs
        # For now, if browser is running, we assume it might be our app
        return 0  # Browser is open
    fi
    return 1  # No browser found
}

# Function to check if web server is ready
is_web_ready() {
    curl -s -o /dev/null -w "%{http_code}" "$WEB_URL" | grep -q "200\|404"  # 404 is OK, means server is up
}

# Function to open browser
open_browser() {
    # Try to get the display
    export DISPLAY=:0
    
    # Check if we have a display
    if [ -z "$DISPLAY" ] || ! xset q &>/dev/null; then
        echo "No display available, skipping browser launch"
        return 1
    fi
    
    # Try different browser commands
    # Use app mode for a cleaner experience (no browser UI)
    if command -v chromium-browser &> /dev/null; then
        # Chromium on Raspberry Pi - app mode (no browser chrome)
        chromium-browser --app="$WEB_URL" --start-fullscreen --disable-infobars --noerrdialogs --disable-session-crashed-bubble 2>/dev/null &
    elif command -v chromium &> /dev/null; then
        chromium --app="$WEB_URL" --start-fullscreen --disable-infobars --noerrdialogs --disable-session-crashed-bubble 2>/dev/null &
    elif command -v google-chrome &> /dev/null; then
        google-chrome --app="$WEB_URL" --start-fullscreen --disable-infobars --noerrdialogs --disable-session-crashed-bubble 2>/dev/null &
    elif command -v firefox &> /dev/null; then
        # Firefox kiosk mode
        firefox --kiosk "$WEB_URL" 2>/dev/null &
    elif command -v xdg-open &> /dev/null; then
        # Fallback to default browser
        xdg-open "$WEB_URL" 2>/dev/null &
    else
        echo "No suitable browser found"
        return 1
    fi
    
    echo "Browser launched: $WEB_URL"
    return 0
}

# Main logic
main() {
    # Check if auto-launch is enabled
    if [ "$LEROY_AUTO_LAUNCH_BROWSER" != "true" ]; then
        echo "Browser auto-launch is disabled (LEROY_AUTO_LAUNCH_BROWSER=false)"
        return 0
    fi
    
    # Wait for web server to be ready
    echo "Waiting for web server to be ready on ${WEB_URL}..."
    waited=0
    while [ $waited -lt $MAX_WAIT ]; do
        if is_web_ready; then
            echo "Web server is ready"
            break
        fi
        sleep $CHECK_INTERVAL
        waited=$((waited + CHECK_INTERVAL))
    done
    
    if [ $waited -ge $MAX_WAIT ]; then
        echo "Web server not ready after ${MAX_WAIT}s, skipping browser launch"
        return 1
    fi
    
    # Check if browser is already open
    if is_browser_open; then
        echo "Browser already open to web app, skipping launch"
        return 0
    fi
    
    # Open browser
    open_browser
}

# Run main function
main "$@"

