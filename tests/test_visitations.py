"""
Tests for visitation tracking logic.
Tests core business logic for visitations.
"""
import unittest
import sys
import os
import time
import numpy as np
from unittest.mock import patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visitations import Visitations


class TestVisitations(unittest.TestCase):
    """Test Visitations tracking functionality."""

    def setUp(self):
        """Set up test fixtures."""
        from collections import namedtuple
        BBox = namedtuple('BBox', ['xmin', 'ymin', 'xmax', 'ymax'])
        Object = namedtuple('Object', ['id', 'score', 'bbox'])

        self.visitations = Visitations()
        bbox = BBox(xmin=0.2, ymin=0.3, xmax=0.6, ymax=0.7)
        self.mock_obj = Object(id=14, score=0.85, bbox=bbox)
        # Real numpy frame (MagicMock.copy() returns mock without shape)
        self.frame = np.zeros((1536, 2048, 3), dtype=np.uint8)

    @patch('visitations.capture')
    def test_visitation_creation(self, mock_capture):
        """Test that visitation is created when bird detected."""
        labels = {14: "bird"}
        objs = [self.mock_obj]
        self.visitations.update(objs, self.frame, labels)
        
        # Visitation should be created
        self.assertIsNotNone(self.visitations.visitation_id)
        self.assertEqual(self.visitations.photo_per_visitation_count, 1)

    @patch('visitations.capture')
    def test_photo_limit(self, mock_capture):
        """Test that photo count respects limit."""
        labels = {14: "bird"}
        objs = [self.mock_obj]

        # Set limit to 2 for testing
        self.visitations.photo_per_visitation_max = 2

        # First photo (creates visitation)
        self.visitations.update(objs, self.frame, labels)
        self.assertEqual(self.visitations.photo_per_visitation_count, 1)

        # Second photo
        self.visitations.update(objs, self.frame, labels)
        self.assertEqual(self.visitations.photo_per_visitation_count, 2)

        # Third photo should not increment (at limit)
        self.visitations.started_tracking = time.time()
        self.visitations.update(objs, self.frame, labels)
        self.assertEqual(self.visitations.photo_per_visitation_count, 2, "Photo count should not exceed max")

    @patch('visitations.capture')
    def test_visitation_reset(self, mock_capture):
        """Test that visitation resets correctly."""
        labels = {14: "bird"}
        objs = [self.mock_obj]

        # Create visitation
        self.visitations.update(objs, self.frame, labels)

        # Reset
        self.visitations.reset()
        
        # Should be reset
        self.assertIsNone(self.visitations.visitation_id)
        self.assertEqual(self.visitations.photo_per_visitation_count, 0)
        self.assertEqual(self.visitations.full_photo_per_visitation_count, 0)

    @patch('visitations.capture')
    def test_visitation_timeout(self, mock_capture):
        """Test that visitation times out after max seconds."""
        labels = {14: "bird"}
        objs = [self.mock_obj]

        # Create visitation
        self.visitations.update(objs, self.frame, labels)
        self.visitations.vistation_max_seconds = 1.0  # 1 second for testing

        # Wait past timeout
        time.sleep(1.1)

        # Update without bird (simulates bird leaving)
        self.visitations.update([], self.frame, labels)

        self.assertIsNone(self.visitations.visitation_id, "Visitation should reset after timeout when bird leaves")


if __name__ == '__main__':
    unittest.main()

