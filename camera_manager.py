"""
Camera Manager for Project Leroy
Handles dual-resolution strategy: configurable detection and photo resolutions.
Uses picamera2 (libcamera) for Pi 5 + Bookworm compatibility.
"""
import logging
import time
import threading
from typing import Optional, Tuple, Callable
import numpy as np
from picamera2 import Picamera2
from config import get_config

logger = logging.getLogger(__name__)


class CameraManager:
    """
    Manages camera with dual-resolution strategy:
    - Detection: Configurable resolution for fast capture, resized to 500px for inference
    - Photos: Configurable high-resolution for quality captures when bird detected
    """

    def __init__(self, camera_idx: int = 0, max_reconnect_attempts: int = 5):
        """
        Initialize camera manager.

        Args:
            camera_idx: Camera device index (mapped to picamera2 camera_num)
            max_reconnect_attempts: Maximum reconnection attempts
        """
        config = get_config()
        self.camera_idx = camera_idx
        self.max_reconnect_attempts = max_reconnect_attempts
        self.picam2: Optional[Picamera2] = None
        self.detection_resolution = config['detection_resolution']
        self.photo_resolution = config['photo_resolution']
        self.current_resolution = self.detection_resolution
        self.consecutive_failures = 0
        self._lock = threading.Lock()
        self._photo_capture_pending = False
        self._photo_callback: Optional[Callable] = None
        self._preview_config = None
        self._still_config = None

    def initialize(self) -> bool:
        """Initialize camera at detection resolution."""
        return self._open_camera(self.detection_resolution)

    def _build_configs(self, resolution: Tuple[int, int]):
        """Build picamera2 configurations for the given resolution."""
        width, height = resolution
        self._preview_config = self.picam2.create_preview_configuration(
            main={"size": (width, height), "format": "BGR888"}
        )
        photo_width, photo_height = self.photo_resolution
        self._still_config = self.picam2.create_still_configuration(
            main={"size": (photo_width, photo_height), "format": "BGR888"}
        )

    def _open_camera(self, resolution: Tuple[int, int]) -> bool:
        """Open camera at specified resolution."""
        try:
            if self.picam2 is not None:
                try:
                    self.picam2.stop()
                    self.picam2.close()
                except Exception as e:
                    logger.warning(f"Error closing existing picamera2 instance: {e}")
                self.picam2 = None

            self.picam2 = Picamera2(camera_num=self.camera_idx)
            self._build_configs(resolution)
            self.picam2.configure(self._preview_config)
            self.picam2.start()

            # Verify resolution by capturing one frame
            frame = self.picam2.capture_array()
            if frame is None:
                logger.error("Camera opened but capture_array returned None")
                return False

            actual_height, actual_width = frame.shape[:2]
            self.current_resolution = (actual_width, actual_height)
            logger.info(f"Camera opened at {actual_width}x{actual_height}")

            # Warm up camera (capture a few frames to stabilize)
            for _ in range(2):
                self.picam2.capture_array()

            self.consecutive_failures = 0
            return True

        except Exception as e:
            logger.error(f"Error opening camera: {e}")
            return False

    def get_detection_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Get frame at detection resolution.

        Returns:
            (success, frame) tuple. Frame is a BGR numpy array.
        """
        with self._lock:
            if self.picam2 is None:
                if not self._reconnect():
                    return False, None

            try:
                frame = self.picam2.capture_array()
            except Exception as e:
                logger.error(f"Error capturing frame: {e}")
                frame = None

            if frame is not None:
                self.consecutive_failures = 0
                return True, frame
            else:
                self.consecutive_failures += 1
                if self.consecutive_failures >= 3:
                    logger.warning("Multiple consecutive frame read failures, attempting reconnect")
                    try:
                        self.picam2.stop()
                        self.picam2.close()
                    except Exception as e:
                        logger.warning(f"Error closing camera during reconnect: {e}")
                    self.picam2 = None
                    if not self._reconnect():
                        return False, None
                return False, None

    def capture_high_res_photo(self, callback: Callable[[np.ndarray], None]) -> bool:
        """
        Capture a high-resolution photo.
        Uses threading to avoid blocking detection loop.

        Args:
            callback: Function to call with the high-res BGR frame

        Returns:
            True if capture was queued, False otherwise
        """
        if self._photo_capture_pending:
            logger.warning("Photo capture already pending, skipping")
            return False

        self._photo_capture_pending = True
        self._photo_callback = callback

        # Capture in background thread
        thread = threading.Thread(
            target=self._capture_high_res_thread,
            daemon=True,
            name="HighResCapture"
        )
        thread.start()

        return True

    def _capture_high_res_thread(self):
        """Background thread to capture high-resolution photo."""
        try:
            logger.info("Switching to photo resolution mode for capture")

            # Switch to photo resolution and capture
            with self._lock:
                try:
                    frame = self.picam2.switch_mode_and_capture_array(self._still_config)
                except Exception as e:
                    logger.error(f"Failed to switch to photo resolution mode: {e}")
                    self._photo_capture_pending = False
                    return

                if frame is not None:
                    logger.info(f"Captured photo frame: {frame.shape[1]}x{frame.shape[0]}")
                    # Call callback with high-res frame
                    if self._photo_callback:
                        self._photo_callback(frame)
                else:
                    logger.error("Failed to capture photo frame")

                # Switch back to detection resolution
                logger.info("Switching back to detection resolution")
                self._switch_resolution(self.detection_resolution)

            self._photo_capture_pending = False

        except Exception as e:
            logger.exception(f"Error in photo capture thread: {e}")
            self._photo_capture_pending = False
            # Try to switch back to detection resolution
            try:
                with self._lock:
                    self._switch_resolution(self.detection_resolution)
            except Exception:
                pass

    def _switch_resolution(self, resolution: Tuple[int, int]) -> bool:
        """
        Switch camera to specified resolution.

        Args:
            resolution: (width, height) tuple

        Returns:
            True if successful
        """
        if self.current_resolution == resolution:
            return True  # Already at this resolution

        try:
            width, height = resolution
            preview_config = self.picam2.create_preview_configuration(
                main={"size": (width, height), "format": "BGR888"}
            )
            self.picam2.switch_mode(preview_config)
            self.current_resolution = resolution

            # Warm up (capture a few frames)
            for _ in range(2):
                self.picam2.capture_array()

            logger.info(f"Switched to {width}x{height}")
            return True

        except Exception as e:
            logger.error(f"Error switching resolution: {e}")
            return False

    def _reconnect(self) -> bool:
        """Attempt to reconnect to camera."""
        for attempt in range(self.max_reconnect_attempts):
            try:
                logger.info(f"Attempting camera reconnection (attempt {attempt + 1}/{self.max_reconnect_attempts})")

                if self._open_camera(self.current_resolution):
                    return True

            except Exception as e:
                logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")

            time.sleep(2)  # Wait before retry

        logger.error("Failed to reconnect to camera after all attempts")
        return False

    def release(self):
        """Release camera resources."""
        with self._lock:
            if self.picam2 is not None:
                try:
                    self.picam2.stop()
                    self.picam2.close()
                except Exception as e:
                    logger.warning(f"Error releasing camera: {e}")
                self.picam2 = None
            self._photo_capture_pending = False

    def get_current_resolution(self) -> Tuple[int, int]:
        """Get current camera resolution."""
        return self.current_resolution

    def is_photo_capture_pending(self) -> bool:
        """Check if photo capture is in progress."""
        return self._photo_capture_pending

    def get_detection_resolution(self) -> Tuple[int, int]:
        """Get detection resolution."""
        return self.detection_resolution

    def get_photo_resolution(self) -> Tuple[int, int]:
        """Get photo resolution."""
        return self.photo_resolution
