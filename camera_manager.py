"""
Camera Manager for Project Leroy
Handles dual-resolution strategy: 5MP for detection, 12MP for photos
"""
import cv2
import logging
import time
import threading
from typing import Optional, Tuple, Callable
import numpy as np

logger = logging.getLogger(__name__)


class CameraManager:
    """
    Manages camera with dual-resolution strategy:
    - Detection: 1.2MP (1280x960) for fast capture, resized to 500px for inference
    - Photos: 12MP (4056x3040) for high-quality captures when bird detected
    """
    
    # Resolution presets
    # Detection: Smaller resolution for fast capture, will be resized to 500px anyway
    # Using 1280x960 (1.2MP) - much smaller than 5MP, still good quality for detection
    DETECTION_RESOLUTION = (1280, 960)  # 1.2MP - fast capture, resized to 500px for inference
    PHOTO_RESOLUTION = (4056, 3040)     # 12MP - high quality photos
    
    def __init__(self, camera_idx: int = 0, max_reconnect_attempts: int = 5):
        """
        Initialize camera manager.
        
        Args:
            camera_idx: Camera device index
            max_reconnect_attempts: Maximum reconnection attempts
        """
        self.camera_idx = camera_idx
        self.max_reconnect_attempts = max_reconnect_attempts
        self.cap = None
        self.current_resolution = self.DETECTION_RESOLUTION
        self.consecutive_failures = 0
        self._lock = threading.Lock()
        self._photo_capture_pending = False
        self._photo_callback: Optional[Callable] = None
        
    def initialize(self) -> bool:
        """Initialize camera at detection resolution."""
        return self._open_camera(self.DETECTION_RESOLUTION)
    
    def _open_camera(self, resolution: Tuple[int, int]) -> bool:
        """Open camera at specified resolution."""
        width, height = resolution
        
        try:
            if self.cap is not None:
                self.cap.release()
            
            self.cap = cv2.VideoCapture(self.camera_idx)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera {self.camera_idx}")
                return False
            
            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Verify resolution
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            self.current_resolution = (actual_width, actual_height)
            logger.info(f"Camera opened at {actual_width}x{actual_height}")
            
            # Warm up camera (read a few frames to stabilize)
            for _ in range(3):
                self.cap.read()
            
            self.consecutive_failures = 0
            return True
            
        except Exception as e:
            logger.error(f"Error opening camera: {e}")
            return False
    
    def get_detection_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Get frame at detection resolution (5MP).
        
        Returns:
            (success, frame) tuple
        """
        with self._lock:
            if self.cap is None or not self.cap.isOpened():
                if not self._reconnect():
                    return False, None
            
            ret, frame = self.cap.read()
            
            if ret:
                self.consecutive_failures = 0
                return True, frame
            else:
                self.consecutive_failures += 1
                if self.consecutive_failures >= 3:
                    logger.warning("Multiple consecutive frame read failures, attempting reconnect")
                    self.cap.release()
                    self.cap = None
                    if not self._reconnect():
                        return False, None
                return False, None
    
    def capture_high_res_photo(self, callback: Callable[[cv2.Mat], None]) -> bool:
        """
        Capture a high-resolution (12MP) photo.
        Uses threading to avoid blocking detection loop.
        
        Args:
            callback: Function to call with the high-res frame
            
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
            logger.info("Switching to high-resolution mode for photo capture")
            
            # Switch to high resolution
            with self._lock:
                if not self._switch_resolution(self.PHOTO_RESOLUTION):
                    logger.error("Failed to switch to high-resolution mode")
                    self._photo_capture_pending = False
                    return
                
                # Capture frame
                ret, frame = self.cap.read()
                
                if ret:
                    logger.info(f"Captured high-res frame: {frame.shape[1]}x{frame.shape[0]}")
                    # Call callback with high-res frame
                    if self._photo_callback:
                        self._photo_callback(frame)
                else:
                    logger.error("Failed to capture high-res frame")
                
                # Switch back to detection resolution
                logger.info("Switching back to detection resolution")
                self._switch_resolution(self.DETECTION_RESOLUTION)
            
            self._photo_capture_pending = False
            
        except Exception as e:
            logger.exception(f"Error in high-res capture thread: {e}")
            self._photo_capture_pending = False
            # Try to switch back to detection resolution
            try:
                with self._lock:
                    self._switch_resolution(self.DETECTION_RESOLUTION)
            except:
                pass
    
    def _switch_resolution(self, resolution: Tuple[int, int]) -> bool:
        """
        Switch camera to specified resolution.
        
        Args:
            resolution: (width, height) tuple
            
        Returns:
            True if successful
        """
        width, height = resolution
        
        if self.current_resolution == resolution:
            return True  # Already at this resolution
        
        try:
            # Release and reopen for clean resolution change
            if self.cap is not None:
                self.cap.release()
            
            self.cap = cv2.VideoCapture(self.camera_idx)
            
            if not self.cap.isOpened():
                logger.error("Failed to reopen camera for resolution change")
                return False
            
            # Set new resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Verify
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            self.current_resolution = (actual_width, actual_height)
            
            # Warm up (read a few frames)
            for _ in range(2):
                self.cap.read()
            
            logger.info(f"Switched to {actual_width}x{actual_height}")
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
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            self._photo_capture_pending = False
    
    def get_current_resolution(self) -> Tuple[int, int]:
        """Get current camera resolution."""
        return self.current_resolution
    
    def is_photo_capture_pending(self) -> bool:
        """Check if high-res photo capture is in progress."""
        return self._photo_capture_pending

