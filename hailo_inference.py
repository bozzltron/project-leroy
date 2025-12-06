"""
Hailo AI Kit inference module for Project Leroy.
Uses official Raspberry Pi Hailo SDK.
"""
import logging
import numpy as np
import cv2
from typing import List, Tuple, Optional, Dict
from PIL import Image

logger = logging.getLogger(__name__)

try:
    from hailo_platform import Device, InferVStreams, HEF
    HAILO_AVAILABLE = True
    HAILO_IMPORT_ERROR = None
except ImportError as e:
    HAILO_AVAILABLE = False
    HAILO_IMPORT_ERROR = str(e)
    # Try alternative import (some SDK versions may have different names)
    try:
        from hailo_platform import Device, InferVStreams
        # HEF might be in a different module or named differently
        HEF = None  # Will handle this in load methods
        HAILO_AVAILABLE = True
        HAILO_IMPORT_ERROR = None
    except ImportError:
        pass
    import sys
    logger.warning(f"Hailo SDK not available at import time. Import error: {e}")
    logger.warning(f"Python executable: {sys.executable}")
    logger.warning(f"Python version: {sys.version}")


class HailoInference:
    """
    Hailo AI Kit inference using official Raspberry Pi SDK.
    
    This class provides an interface for running detection and classification
    models on the Hailo-8L accelerator via the Raspberry Pi AI Kit.
    """
    
    def __init__(self):
        """Initialize Hailo inference engine."""
        global HAILO_AVAILABLE, HAILO_IMPORT_ERROR
        
        if not HAILO_AVAILABLE:
            import sys
            import os
            
            # Try importing again at runtime (in case environment changed)
            try:
                from hailo_platform import Device, InferVStreams, HEF
                # Success! Update the global flag
                HAILO_AVAILABLE = True
                logger.info("Hailo SDK successfully imported at runtime")
            except ImportError:
                # Try without HEF (might be in different module)
                try:
                    from hailo_platform import Device, InferVStreams
                    HEF = None  # Will handle in load methods
                    HAILO_AVAILABLE = True
                    logger.info("Hailo SDK imported (without HEF class)")
                except ImportError as e:
                    # Still failing - provide detailed diagnostics
                    import_error = HAILO_IMPORT_ERROR if HAILO_IMPORT_ERROR else str(e)
                    error_msg = (
                        "Hailo SDK not available.\n"
                        f"\n"
                        f"Import error: {import_error}\n"
                        f"\n"
                        f"Diagnostics:\n"
                        f"  Python executable: {sys.executable}\n"
                        f"  Python version: {sys.version}\n"
                        f"  Virtual environment: {os.environ.get('VIRTUAL_ENV', 'Not set')}\n"
                        f"  PATH: {os.environ.get('PATH', 'Not set')}\n"
                        f"\n"
                        f"Python sys.path:\n"
                    )
                    for path in sys.path:
                        error_msg += f"  - {path}\n"
                    
                    error_msg += (
                        f"\n"
                        f"To fix:\n"
                        f"1. Verify Hailo SDK is installed system-wide:\n"
                        f"   /usr/bin/python3 -c 'from hailo_platform import Device; print(\"OK\")'\n"
                        f"\n"
                        f"2. If system-wide works, ensure venv has --system-site-packages:\n"
                        f"   Check: grep 'include-system-site-packages' venv/pyvenv.cfg\n"
                        f"   Should show: include-system-site-packages = true\n"
                        f"\n"
                        f"3. If venv doesn't have system-site-packages, recreate it:\n"
                        f"   rm -rf venv\n"
                        f"   python3 -m venv --system-site-packages venv\n"
                        f"   source venv/bin/activate\n"
                        f"   pip install --upgrade pip setuptools wheel\n"
                        f"   pip install numpy pillow opencv-contrib-python psutil imutils\n"
                        f"\n"
                        f"4. Verify from venv:\n"
                        f"   venv/bin/python3 -c 'from hailo_platform import Device; print(\"OK\")'\n"
                        f"\n"
                        f"5. Follow official guide if still failing:\n"
                        f"   https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
        
        self.device = None
        self.detection_network = None
        self.classification_network = None
        self._initialized = False
    
    def initialize(self, device_id: Optional[str] = None):
        """
        Initialize Hailo device.
        
        Args:
            device_id: Optional device ID to use. If None, uses default device.
        """
        if self._initialized:
            return
        
        # First, check if device is accessible via hailortcli
        import subprocess
        try:
            result = subprocess.run(
                ['hailortcli', 'fw-control', 'identify'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                # Check for driver version mismatch
                if 'Driver version' in result.stderr and 'library version' in result.stderr:
                    logger.error("Driver/library version mismatch detected.")
                    logger.error("Run: sudo apt-get install --reinstall hailo-all && sudo reboot")
                    raise RuntimeError("Driver version mismatch - reinstall hailo-all and reboot")
                else:
                    logger.warning(f"hailortcli identify failed: {result.stderr}")
            else:
                logger.info(f"Hailo device identified: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.warning("hailortcli not found - cannot verify device before initialization")
        except Exception as e:
            logger.warning(f"Could not verify device with hailortcli: {e}")
        
        try:
            # Try to initialize device (with or without device_id)
            if device_id is not None:
                logger.info(f"Initializing Hailo device with ID: {device_id}")
                self.device = Device(device_id=device_id)
            else:
                logger.info("Initializing Hailo device (default)")
                self.device = Device()
            
            logger.info("Hailo device initialized successfully")
            self._initialized = True
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to initialize Hailo device: {e}")
            
            # Provide simple, actionable error message
            if '76' in error_msg or 'INVALID_DRIVER_VERSION' in error_msg or 'Driver version' in error_msg:
                logger.error("")
                logger.error("Driver/library version mismatch detected.")
                logger.error("This MUST be fixed before the service can run:")
                logger.error("  1. Run: sudo apt-get update")
                logger.error("  2. Run: sudo apt-get install --reinstall hailo-all")
                logger.error("  3. Reboot: sudo reboot")
                logger.error("  4. Verify: sudo hailortcli fw-control identify")
                logger.error("")
                logger.error("The install script should have done this - if it didn't, run it again.")
            else:
                logger.error("")
                logger.error("Device not accessible. Check:")
                logger.error("  1. Hardware connected: sudo hailortcli fw-control identify")
                logger.error("  2. PCIe configured: grep pcie_gen3 /boot/firmware/config.txt")
                logger.error("  3. Try specifying device ID if multiple devices: Device(device_id='...')")
                logger.error("  4. Reboot may be required after installation")
            
            raise
    
    def load_detection_model(self, model_path: str) -> None:
        """
        Load detection model (HEF format).
        
        Args:
            model_path: Path to HEF model file
        """
        if not self._initialized:
            self.initialize()
        
        try:
            # Hailo SDK API: Load HEF file and configure on device
            # Method 1: Using HEF class (preferred)
            if HEF is not None:
                try:
                    # Try HEF.from_file() first (common API)
                    hef = HEF.from_file(model_path)
                    self.detection_network = self.device.configure(hef)
                except (AttributeError, TypeError):
                    # Try HEF() constructor
                    try:
                        hef = HEF(model_path)
                        self.detection_network = self.device.configure(hef)
                    except (AttributeError, TypeError):
                        # Try direct file path
                        hef = HEF.from_file(model_path) if hasattr(HEF, 'from_file') else HEF(model_path)
                        self.detection_network = self.device.configure(hef)
            else:
                # Method 2: Try device.load_model() (if available in some SDK versions)
                if hasattr(self.device, 'load_model'):
                    self.detection_network = self.device.load_model(model_path)
                # Method 3: Try device.configure() with file path directly
                elif hasattr(self.device, 'configure'):
                    self.detection_network = self.device.configure(model_path)
                else:
                    # Method 4: Try importing HEF dynamically
                    try:
                        from hailo_platform import HEF as HEFClass
                        hef = HEFClass.from_file(model_path) if hasattr(HEFClass, 'from_file') else HEFClass(model_path)
                        self.detection_network = self.device.configure(hef)
                    except Exception as e2:
                        raise RuntimeError(
                            f"Could not load model using any known API. "
                            f"Device methods: {[m for m in dir(self.device) if not m.startswith('_')]}. "
                            f"Error: {e2}"
                        )
            
            logger.info(f"Loaded detection model: {model_path}")
        except Exception as e:
            logger.error(f"Failed to load detection model {model_path}: {e}")
            logger.error(f"Device type: {type(self.device)}")
            logger.error(f"Device methods: {[m for m in dir(self.device) if not m.startswith('_')]}")
            raise
    
    def load_classification_model(self, model_path: str) -> None:
        """
        Load classification model (HEF format).
        
        Args:
            model_path: Path to HEF model file
        """
        if not self._initialized:
            self.initialize()
        
        try:
            # Hailo SDK API: Load HEF file and configure on device
            # Method 1: Using HEF class (preferred)
            if HEF is not None:
                try:
                    # Try HEF.from_file() first (common API)
                    hef = HEF.from_file(model_path)
                    self.classification_network = self.device.configure(hef)
                except (AttributeError, TypeError):
                    # Try HEF() constructor
                    try:
                        hef = HEF(model_path)
                        self.classification_network = self.device.configure(hef)
                    except (AttributeError, TypeError):
                        # Try direct file path
                        hef = HEF.from_file(model_path) if hasattr(HEF, 'from_file') else HEF(model_path)
                        self.classification_network = self.device.configure(hef)
            else:
                # Method 2: Try device.load_model() (if available in some SDK versions)
                if hasattr(self.device, 'load_model'):
                    self.classification_network = self.device.load_model(model_path)
                # Method 3: Try device.configure() with file path directly
                elif hasattr(self.device, 'configure'):
                    self.classification_network = self.device.configure(model_path)
                else:
                    # Method 4: Try importing HEF dynamically
                    try:
                        from hailo_platform import HEF as HEFClass
                        hef = HEFClass.from_file(model_path) if hasattr(HEFClass, 'from_file') else HEFClass(model_path)
                        self.classification_network = self.device.configure(hef)
                    except Exception as e2:
                        raise RuntimeError(
                            f"Could not load model using any known API. "
                            f"Device methods: {[m for m in dir(self.device) if not m.startswith('_')]}. "
                            f"Error: {e2}"
                        )
            
            logger.info(f"Loaded classification model: {model_path}")
        except Exception as e:
            logger.error(f"Failed to load classification model {model_path}: {e}")
            logger.error(f"Device type: {type(self.device)}")
            logger.error(f"Device methods: {[m for m in dir(self.device) if not m.startswith('_')]}")
            raise
    
    def detect(self, image: Image.Image, score_threshold: float = 0.1, top_k: int = 3) -> List[dict]:
        """
        Run detection inference on image.
        
        Args:
            image: PIL Image to process
            score_threshold: Minimum confidence score
            top_k: Maximum number of detections to return
            
        Returns:
            List of detection dictionaries with keys: id, score, bbox
        """
        if self.detection_network is None:
            raise RuntimeError("Detection model not loaded")
        
        try:
            # Preprocess image for model input
            input_data = self._preprocess_image(image, self.detection_network)
            
            # Run inference
            # InferVStreams expects input as dictionary of input tensor names to arrays
            with InferVStreams(self.detection_network) as infer_pipeline:
                # Infer returns dictionary of output tensor names to numpy arrays
                results = infer_pipeline.infer(input_data)
            
            # Postprocess results
            detections = self._postprocess_detection(results, score_threshold, top_k)
            return detections
            
        except Exception as e:
            logger.error(f"Detection inference failed: {e}")
            raise
    
    def classify(self, image: Image.Image, top_k: int = 3, threshold: float = 0.1) -> List[Tuple[int, float]]:
        """
        Run classification inference on image.
        
        Args:
            image: PIL Image to process
            top_k: Number of top classifications to return
            threshold: Minimum confidence score
            
        Returns:
            List of tuples (class_id, score)
        """
        if self.classification_network is None:
            raise RuntimeError("Classification model not loaded")
        
        try:
            # Preprocess image for model input
            input_data = self._preprocess_image(image, self.classification_network)
            
            # Run inference
            # InferVStreams expects input as dictionary of input tensor names to arrays
            with InferVStreams(self.classification_network) as infer_pipeline:
                # Infer returns dictionary of output tensor names to numpy arrays
                results = infer_pipeline.infer(input_data)
            
            # Postprocess results
            classifications = self._postprocess_classification(results, top_k, threshold)
            return classifications
            
        except Exception as e:
            logger.error(f"Classification inference failed: {e}")
            raise
    
    def _preprocess_image(self, image: Image.Image, network) -> dict:
        """
        Preprocess image for model input.
        
        Args:
            image: PIL Image
            network: Hailo network object (to get input shape)
            
        Returns:
            Dictionary of input tensor names to preprocessed numpy arrays
        """
        # Try to get input shape from network
        # Hailo SDK typically provides input_vstreams() method
        try:
            # Get input vstream info to determine input shape
            input_vstreams = network.get_input_vstream_infos()
            if input_vstreams:
                # Get first input vstream shape
                input_shape = input_vstreams[0].shape
                height, width = input_shape[1], input_shape[2]  # Typically (batch, height, width, channels)
            else:
                # Fallback: try common detection/classification input sizes
                # Detection models often use 300x300 or 320x320
                # Classification models often use 224x224
                if self.detection_network is not None:
                    height, width = 300, 300  # Common SSD input size
                else:
                    height, width = 224, 224  # Common classification input size
        except (AttributeError, IndexError):
            # Fallback to default sizes
            if self.detection_network is not None:
                height, width = 300, 300
            else:
                height, width = 224, 224
        
        # Resize image to model input size (maintain aspect ratio if needed)
        # For detection models, we typically resize to fixed size
        resized = image.resize((width, height), Image.LANCZOS)
        
        # Convert to numpy array
        # PIL Image is RGB, keep as RGB (most Hailo models expect RGB)
        img_array = np.asarray(resized, dtype=np.uint8)
        
        # Note: PIL Image is RGB format, which is what most Hailo models expect
        # If model was trained on BGR (OpenCV), uncomment below:
        # if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        #     img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Normalize to [0, 1] range (float32)
        img_array = img_array.astype(np.float32) / 255.0
        
        # Hailo SDK expects input as dictionary of tensor names to arrays
        # Try to get input tensor name from network
        try:
            input_vstreams = network.get_input_vstream_infos()
            if input_vstreams:
                input_name = input_vstreams[0].name
            else:
                input_name = 'input'  # Default name
        except (AttributeError, IndexError):
            input_name = 'input'
        
        # Return as dictionary (Hailo SDK expects this format)
        return {input_name: img_array}
    
    def _postprocess_detection(self, results, score_threshold: float, top_k: int) -> List[dict]:
        """
        Postprocess detection results from Hailo inference.
        
        Args:
            results: Raw inference results from Hailo (dict of output tensor names to arrays)
            score_threshold: Minimum confidence score
            top_k: Maximum number of detections
            
        Returns:
            List of detection dictionaries with keys: id, score, bbox
            bbox format: {'xmin': float, 'ymin': float, 'xmax': float, 'ymax': float} (normalized 0-1)
        """
        detections = []
        
        try:
            # Hailo SDK returns results as dictionary of output tensor names to numpy arrays
            # For SSD models, typical outputs are:
            # - 'detection_boxes': [num_detections, 4] (ymin, xmin, ymax, xmax) normalized
            # - 'detection_scores': [num_detections] confidence scores
            # - 'detection_classes': [num_detections] class IDs
            
            # Try to extract output tensors
            if isinstance(results, dict):
                # Get output tensors
                boxes = None
                scores = None
                classes = None
                
                # Try common output tensor names
                for key in results.keys():
                    key_lower = key.lower()
                    if 'box' in key_lower or 'bbox' in key_lower:
                        boxes = results[key]
                    elif 'score' in key_lower or 'confidence' in key_lower:
                        scores = results[key]
                    elif 'class' in key_lower or 'label' in key_lower:
                        classes = results[key]
                
                # If not found by name, try to infer from shape
                if boxes is None or scores is None or classes is None:
                    output_keys = list(results.keys())
                    if len(output_keys) >= 3:
                        # Assume order: boxes, scores, classes
                        boxes = results[output_keys[0]]
                        scores = results[output_keys[1]]
                        classes = results[output_keys[2]]
                    elif len(output_keys) == 1:
                        # Single output tensor - might be combined format
                        # Some models output [num_detections, 6] where columns are:
                        # [xmin, ymin, xmax, ymax, score, class]
                        combined = results[output_keys[0]]
                        if len(combined.shape) == 2 and combined.shape[1] >= 6:
                            boxes = combined[:, :4]
                            scores = combined[:, 4]
                            classes = combined[:, 5].astype(np.int32)
                
                # Process detections
                if boxes is not None and scores is not None and classes is not None:
                    # Ensure arrays are numpy arrays
                    boxes = np.asarray(boxes)
                    scores = np.asarray(scores)
                    classes = np.asarray(classes).astype(np.int32)
                    
                    # Flatten if needed
                    if len(scores.shape) > 1:
                        scores = scores.flatten()
                    if len(classes.shape) > 1:
                        classes = classes.flatten()
                    
                    # Filter by score threshold
                    valid_indices = scores >= score_threshold
                    boxes = boxes[valid_indices]
                    scores = scores[valid_indices]
                    classes = classes[valid_indices]
                    
                    # Sort by score descending
                    sorted_indices = np.argsort(scores)[::-1]
                    boxes = boxes[sorted_indices]
                    scores = scores[sorted_indices]
                    classes = classes[sorted_indices]
                    
                    # Take top_k
                    num_detections = min(top_k, len(scores))
                    
                    # Convert to detection format
                    for i in range(num_detections):
                        # Handle different bbox formats
                        bbox = boxes[i]
                        
                        # Normalize bbox coordinates to [0, 1] if needed
                        if len(bbox) == 4:
                            # Check if coordinates are already normalized
                            if bbox.max() > 1.0:
                                # Assume pixel coordinates, need to normalize
                                # But we don't know image size here, so assume already normalized
                                # or use a default image size
                                pass
                            
                            # Handle different bbox formats:
                            # Format 1: [ymin, xmin, ymax, xmax] (SSD format)
                            # Format 2: [xmin, ymin, xmax, ymax] (YOLO format)
                            # Format 3: [center_x, center_y, width, height] (center format)
                            
                            # Try to detect format based on values
                            if bbox[0] < bbox[2] and bbox[1] < bbox[3]:
                                # Likely [ymin, xmin, ymax, xmax] or [xmin, ymin, xmax, ymax]
                                if bbox[0] < bbox[1]:
                                    # [ymin, xmin, ymax, xmax]
                                    ymin, xmin, ymax, xmax = bbox
                                else:
                                    # [xmin, ymin, xmax, ymax]
                                    xmin, ymin, xmax, ymax = bbox
                            else:
                                # Assume [xmin, ymin, xmax, ymax] format
                                xmin, ymin, xmax, ymax = bbox
                            
                            # Ensure values are in [0, 1] range
                            xmin = max(0.0, min(1.0, float(xmin)))
                            ymin = max(0.0, min(1.0, float(ymin)))
                            xmax = max(0.0, min(1.0, float(xmax)))
                            ymax = max(0.0, min(1.0, float(ymax)))
                            
                            detections.append({
                                'id': int(classes[i]),
                                'score': float(scores[i]),
                                'bbox': {
                                    'xmin': xmin,
                                    'ymin': ymin,
                                    'xmax': xmax,
                                    'ymax': ymax
                                }
                            })
            
            elif isinstance(results, np.ndarray):
                # Single numpy array output - try to parse
                # This might be a combined format or single tensor
                logger.warning("Single array output detected - may need model-specific parsing")
                # For now, return empty - would need model-specific knowledge
            
            else:
                logger.warning(f"Unexpected results type: {type(results)}")
        
        except Exception as e:
            logger.error(f"Error in detection postprocessing: {e}")
            logger.exception("Full traceback:")
        
        return detections
    
    def _postprocess_classification(self, results, top_k: int, threshold: float) -> List[Tuple[int, float]]:
        """
        Postprocess classification results from Hailo inference.
        
        Args:
            results: Raw inference results from Hailo (dict of output tensor names to arrays)
            top_k: Number of top classifications
            threshold: Minimum confidence score
            
        Returns:
            List of (class_id, score) tuples, sorted by score descending
        """
        classifications = []
        
        try:
            # Hailo SDK returns results as dictionary of output tensor names to numpy arrays
            # For classification models, output is typically:
            # - Single tensor: [num_classes] probability distribution
            # - Or named output like 'predictions' or 'logits'
            
            # Extract output tensor
            output_array = None
            
            if isinstance(results, dict):
                # Try to find output tensor
                for key in results.keys():
                    key_lower = key.lower()
                    if 'output' in key_lower or 'predict' in key_lower or 'logit' in key_lower or 'prob' in key_lower:
                        output_array = results[key]
                        break
                
                # If not found by name, use first tensor
                if output_array is None and len(results) > 0:
                    output_array = list(results.values())[0]
            
            elif isinstance(results, np.ndarray):
                # Direct numpy array
                output_array = results
            
            # Process output array
            if output_array is not None:
                # Ensure it's a numpy array
                output_array = np.asarray(output_array)
                
                # Flatten if needed (handle batch dimension)
                if len(output_array.shape) > 1:
                    # Take first item if batch dimension exists
                    output_array = output_array[0] if output_array.shape[0] == 1 else output_array.flatten()
                
                # Apply softmax if needed (check if values are logits)
                # If values are negative or very large, they might be logits
                if output_array.min() < 0 or output_array.max() > 1.0:
                    # Likely logits, apply softmax
                    exp_scores = np.exp(output_array - np.max(output_array))  # Numerical stability
                    output_array = exp_scores / np.sum(exp_scores)
                
                # Get top_k indices
                top_indices = np.argsort(output_array)[::-1][:top_k]
                
                # Filter by threshold and create results
                for idx in top_indices:
                    score = float(output_array[idx])
                    if score >= threshold:
                        classifications.append((int(idx), score))
                
                # Sort by score descending (should already be sorted, but ensure)
                classifications.sort(key=lambda x: x[1], reverse=True)
            
            else:
                logger.warning("Could not extract classification output from results")
        
        except Exception as e:
            logger.error(f"Error in classification postprocessing: {e}")
            logger.exception("Full traceback:")
        
        return classifications
    
    def cleanup(self):
        """Clean up resources."""
        self.detection_network = None
        self.classification_network = None
        self.device = None
        self._initialized = False
        logger.info("Hailo inference cleaned up")

