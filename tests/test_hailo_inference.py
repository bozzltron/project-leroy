"""
Tests for YOLO NMS detection postprocessing.

Exercises _postprocess_detection with the Hailo NMS output shapes seen in
production, including the single-element outer wrapper that previously
caused every detection to be silently dropped (regression for the
inhomogeneous-shape ValueError).
"""
import sys
import os
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hailo_inference import HailoInference


class TestNmsPostprocess(unittest.TestCase):
    """Test _postprocess_detection against Hailo NMS output formats."""

    def _hailo(self):
        hailo = HailoInference()
        hailo._initialized = True
        return hailo

    def _empty_per_class(self, num_classes=80):
        return [np.array([]) for _ in range(num_classes)]

    def test_wrapped_per_class_list(self):
        per_class = self._empty_per_class()
        per_class[14] = np.array([[0.1, 0.2, 0.8, 0.9, 0.915]])
        per_class[0] = np.array([[0.0, 0.0, 0.5, 0.5, 0.8]])
        results = {'yolov11s/yolov8_nms_postprocess': [per_class]}

        detections = self._hailo()._postprocess_detection(results, 0.1, 20)

        self.assertEqual(len(detections), 2)
        ids = {d['id'] for d in detections}
        self.assertIn(14, ids)
        self.assertIn(0, ids)
        bird = next(d for d in detections if d['id'] == 14)
        self.assertAlmostEqual(bird['score'], 0.915)
        self.assertEqual(bird['bbox']['xmin'], 0.2)
        self.assertEqual(bird['bbox']['xmax'], 0.9)
        self.assertEqual(bird['bbox']['ymin'], 0.1)
        self.assertEqual(bird['bbox']['ymax'], 0.8)

    def test_unwrapped_per_class_list(self):
        per_class = self._empty_per_class()
        per_class[14] = np.array([[0.1, 0.2, 0.8, 0.9, 0.9]])
        results = {'yolov8_nms_postprocess': per_class}

        detections = self._hailo()._postprocess_detection(results, 0.1, 20)

        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0]['id'], 14)

    def test_no_detections(self):
        per_class = self._empty_per_class()
        results = {'yolov8_nms_postprocess': [per_class]}

        detections = self._hailo()._postprocess_detection(results, 0.1, 20)

        self.assertEqual(detections, [])

    def test_score_threshold(self):
        per_class = self._empty_per_class()
        per_class[14] = np.array([[0.1, 0.2, 0.8, 0.9, 0.3]])
        results = {'yolov8_nms_postprocess': [per_class]}

        detections = self._hailo()._postprocess_detection(results, 0.5, 20)

        self.assertEqual(detections, [])

    def test_multiple_boxes_per_class(self):
        per_class = self._empty_per_class()
        per_class[14] = np.array([
            [0.1, 0.1, 0.4, 0.4, 0.9],
            [0.5, 0.5, 0.9, 0.9, 0.7],
        ])
        results = {'yolov8_nms_postprocess': [per_class]}

        detections = self._hailo()._postprocess_detection(results, 0.1, 20)

        self.assertEqual(len(detections), 2)
        scores = sorted(d['score'] for d in detections)
        self.assertAlmostEqual(scores[0], 0.7)
        self.assertAlmostEqual(scores[1], 0.9)


if __name__ == '__main__':
    unittest.main()
