"""
Hailo AI Kit inference module for Project Leroy.
Uses official Raspberry Pi Hailo SDK.
"""
import logging
import os
import numpy as np
import cv2
from typing import List, Tuple, Optional, Dict
from PIL import Image

logger = logging.getLogger(__name__)

try:
    from hailo_platform import VDevice, InferVStreams, HEF, ConfigureParams, HailoStreamInterface, InputVStreamParams, OutputVStreamParams
    HAILO_AVAILABLE = True
    HAILO_IMPORT_ERROR = None
except ImportError as e:
    HAILO_AVAILABLE = False
    HAILO_IMPORT_ERROR = str(e)


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
            try:
                from hailo_platform import VDevice, InferVStreams, HEF, ConfigureParams, HailoStreamInterface, InputVStreamParams, OutputVStreamParams
                HAILO_AVAILABLE = True
            except ImportError as e:
                err = HAILO_IMPORT_ERROR or str(e)
                raise RuntimeError(
                    f"Hailo SDK not available: {err}. "
                    "Run: ./install-pi5.sh. See: https://www.raspberrypi.com/documentation/accessories/ai-kit.html"
                )
        self.device = None
        self.detection_network = None
        self.classification_network = None
        self._activation_contexts = []  # Track activation contexts for cleanup
        self._initialized = False
    
    def initialize(self, device_id: Optional[str] = None):
        """Initialize Hailo device."""
        if self._initialized:
            return
        try:
            self.device = VDevice(device_id=device_id) if device_id else VDevice()
            self._initialized = True
            logger.info("Hailo device initialized")
        except Exception as e:
            err = str(e)
            if '76' in err or 'Driver version' in err or 'INVALID_DRIVER' in err:
                raise RuntimeError("Hailo driver mismatch. Run: sudo apt-get install --reinstall hailo-all && sudo reboot") from e
            raise RuntimeError(f"Hailo device not accessible: {e}. Run: sudo hailortcli fw-control identify") from e
    
    def _load_model(self, model_path: str) -> object:
        """Load HEF model. Validates path and returns network object."""
        if not self._initialized:
            self.initialize()

        # Resolve relative paths
        if not os.path.isabs(model_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            for base in [script_dir, os.getcwd()]:
                candidate = os.path.join(base, model_path)
                if os.path.exists(candidate):
                    model_path = os.path.abspath(candidate)
                    break

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"HEF not found: {model_path}. Download from https://hailo.ai/products/hailo-software/model-explorer-vision/ (filter: Hailo-8L)")
        if not os.path.isfile(model_path):
            raise ValueError(f"Not a file: {model_path}")
        if os.path.getsize(model_path) == 0:
            raise ValueError(f"HEF empty (0 bytes): {model_path}")
        if not os.access(model_path, os.R_OK):
            raise PermissionError(f"Cannot read: {model_path}")

        logger.info(f"Loading model: {model_path}")
        try:
            hef = HEF(model_path)
            configure_params = ConfigureParams.create_from_hef(hef, HailoStreamInterface.PCIe)
            network_group = self.device.configure(hef, configure_params)[0]
            logger.info(f"Model loaded: {model_path}")
            logger.info(f"Network group: {network_group.name}")
            # Activate the network group (required before inference in HailoRT 4.23.0)
            # Keep the activation context alive but return the ConfiguredNetwork
            # so InputVStreamParams.make() can access its internal methods
            activation_context = network_group.activate()
            activation_context.__enter__()
            self._activation_contexts.append(activation_context)
            logger.info(f"Network group activated: {network_group.name}")
            return network_group
        except Exception as e:
            err = str(e)
            if '93' in err or 'HEF_NOT_COMPATIBLE' in err or 'not compatible' in err.lower():
                raise RuntimeError(f"HEF not compatible with Hailo-8L. Download Hailo-8L models from Model Explorer.") from e
            if '14' in err or 'FILE_OPERATION' in err or 'parsing' in err.lower():
                raise RuntimeError(f"HEF parse failed (corrupted?). Try re-downloading.") from e
            raise

    def load_detection_model(self, model_path: str) -> None:
        """Load detection model (HEF format)."""
        self.detection_network = self._load_model(model_path)

    def load_classification_model(self, model_path: str) -> None:
        """Load classification model (HEF format)."""
        self.classification_network = self._load_model(model_path)
    
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
            # Create vstream params from the configured network group
            input_vstreams_params = InputVStreamParams.make(self.detection_network)
            output_vstreams_params = OutputVStreamParams.make(self.detection_network)
            with InferVStreams(self.detection_network, input_vstreams_params, output_vstreams_params) as infer_pipeline:
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
            # Create vstream params from the configured network group
            input_vstreams_params = InputVStreamParams.make(self.classification_network)
            output_vstreams_params = OutputVStreamParams.make(self.classification_network)
            with InferVStreams(self.classification_network, input_vstreams_params, output_vstreams_params) as infer_pipeline:
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
                # Handle both 3-element (H, W, C) and 4-element (N, H, W, C) shapes
                if len(input_shape) == 4:
                    height, width = input_shape[1], input_shape[2]
                elif len(input_shape) == 3:
                    height, width = input_shape[0], input_shape[1]
                else:
                    raise ValueError(f"Unexpected input shape length: {len(input_shape)}")
            else:
                # Fallback: try common detection/classification input sizes
                if self.detection_network is not None:
                    height, width = 640, 640  # Common YOLO input size
                else:
                    height, width = 224, 224  # Common classification input size
        except (AttributeError, IndexError, ValueError):
            # Fallback to default sizes
            if self.detection_network is not None:
                height, width = 640, 640
            else:
                height, width = 224, 224
        
        # Resize image to model input size (maintain aspect ratio if needed)
        # For detection models, we typically resize to fixed size
        resized = image.resize((width, height), Image.LANCZOS)
        
        # Convert to numpy array
        # PIL Image is RGB, keep as RGB (most Hailo models expect RGB)
        img_array = np.array(resized, dtype=np.uint8)
        
        # Note: PIL Image is RGB format, which is what most Hailo models expect
        # If model was trained on BGR (OpenCV), uncomment below:
        # if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        #     img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Keep as uint8 — Hailo HEF models with quantization handle
        # the uint8-to-float conversion on-chip. Sending float32
        # triggers a runtime warning and unnecessary conversion.

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
        
        # Add batch dimension: (H, W, C) -> (1, H, W, C)
        # HailoRT interprets the first dimension as batch size
        img_array = np.expand_dims(img_array, axis=0)
        return {input_name: img_array}
    
    def _postprocess_detection(self, results, score_threshold: float, top_k: int) -> List[dict]:
        """
        Postprocess detection results from Hailo inference.

        Handles YOLOv11s NMS output format: a dict with one key
        (e.g. 'yolov11s/yolov8_nms_postprocess') whose value is a
        list of per-class numpy arrays, each shape (N, 5) with
        columns [y_min, x_min, y_max, x_max, score].

        Args:
            results: Raw inference results from Hailo
            score_threshold: Minimum confidence score
            top_k: Maximum number of detections to return

        Returns:
            List of detection dicts with keys: id, score, bbox
            bbox: {'xmin', 'ymin', 'xmax', 'ymax'} normalized 0-1
        """
        detections = []

        try:
            if not isinstance(results, dict):
                logger.warning(f"Unexpected results type: {type(results)}")
                return detections

            for output_name, output_value in results.items():
                if isinstance(output_value, list):
                    # NMS format: list of per-class arrays
                    for class_id, class_array in enumerate(output_value):
                        if not isinstance(class_array, np.ndarray):
                            class_array = np.asarray(class_array)
                        if class_array.size == 0 or class_array.shape[0] == 0:
                            continue
                        # Each row: [y_min, x_min, y_max, x_max, score]
                        for row in class_array:
                            if len(row) < 5:
                                continue
                            y_min, x_min, y_max, x_max, score = row[:5]
                            if score < score_threshold:
                                continue
                            detections.append({
                                'id': int(class_id),
                                'score': float(score),
                                'bbox': {
                                    'xmin': float(x_min),
                                    'ymin': float(y_min),
                                    'xmax': float(x_max),
                                    'ymax': float(y_max),
                                }
                            })
                elif isinstance(output_value, np.ndarray):
                    # Single array format (non-NMS or combined)
                    arr = output_value
                    if arr.ndim == 2 and arr.shape[1] >= 6:
                        # [xmin, ymin, xmax, ymax, score, class]
                        for row in arr:
                            if len(row) < 6:
                                continue
                            score = float(row[4])
                            if score < score_threshold:
                                continue
                            detections.append({
                                'id': int(row[5]),
                                'score': score,
                                'bbox': {
                                    'xmin': float(row[0]),
                                    'ymin': float(row[1]),
                                    'xmax': float(row[2]),
                                    'ymax': float(row[3]),
                                }
                            })
                else:
                    logger.debug(f"Unknown output format for {output_name}: {type(output_value)}")

        except Exception as e:
            logger.error(f"Error in detection postprocessing: {e}")
            logger.exception("Full traceback:")

        # Sort by score descending, take top_k
        detections.sort(key=lambda d: d['score'], reverse=True)
        return detections[:top_k]
    
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
        # Deactivate all network groups before releasing device
        for ctx in self._activation_contexts:
            try:
                ctx.__exit__(None, None, None)
            except Exception:
                pass
        self._activation_contexts = []
        self.detection_network = None
        self.classification_network = None
        self.device = None
        self._initialized = False
        logger.info("Hailo inference cleaned up")

