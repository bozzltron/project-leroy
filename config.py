"""
Configuration management for Project Leroy
Loads settings from environment variables and leroy.env file
"""
import os
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def load_config():
    """
    Load configuration from leroy.env file and environment variables.
    Environment variables take precedence over file values.
    """
    config = {}
    
    # Load from leroy.env file if it exists
    env_file = os.path.join(os.path.dirname(__file__), 'leroy.env')
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
        except Exception as e:
            logger.warning(f"Failed to load leroy.env: {e}")
    
    # Camera resolution configuration
    # Detection resolution (for fast capture, will be resized for inference)
    det_width = int(os.environ.get('LEROY_DETECTION_WIDTH', '1280'))
    det_height = int(os.environ.get('LEROY_DETECTION_HEIGHT', '960'))
    config['detection_resolution'] = (det_width, det_height)
    
    # Photo resolution (high quality for saving)
    photo_width = int(os.environ.get('LEROY_PHOTO_WIDTH', '4056'))
    photo_height = int(os.environ.get('LEROY_PHOTO_HEIGHT', '3040'))
    config['photo_resolution'] = (photo_width, photo_height)
    
    # Web server configuration
    config['web_port'] = int(os.environ.get('LEROY_WEB_PORT', '8080'))
    config['web_host'] = os.environ.get('LEROY_WEB_HOST', 'localhost')
    config['auto_launch_browser'] = os.environ.get('LEROY_AUTO_LAUNCH_BROWSER', 'true').lower() == 'true'
    
    # Browser command
    config['browser_cmd'] = os.environ.get('LEROY_BROWSER_CMD', 'chromium-browser')
    
    return config


# Global config instance (loaded on import)
_config = None


def get_config():
    """Get configuration (singleton pattern)."""
    global _config
    if _config is None:
        _config = load_config()
    return _config

