"""
Tests for visitation tracking logic.
Tests core business logic for visitations.
"""
import unittest
import sys
import os
import time
from unittest.mock import Mock, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visitations import Visitations, Visitation


class TestVisitations(unittest.TestCase):
    """Test Visitations tracking functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        from collections import namedtuple
        BBox = namedtuple('BBox', ['xmin', 'ymin', 'xmax', 'ymax'])
        Object = namedtuple('Object', ['id', 'score', 'bbox'])
        
        self.visitations = Visitations()
        # Create Object with BBox (matching leroy.py format)
        bbox = BBox(xmin=0.2, ymin=0.3, xmax=0.6, ymax=0.7)
        self.mock_obj = Object(id=14, score=0.85, bbox=bbox)
    
    def test_visitation_creation(self):
        """Test that visitation is created when bird detected."""
        labels = {14: "bird"}
        frame = MagicMock()
        frame.shape = (1536, 2048, 3)
        
        objs = [self.mock_obj]
        self.visitations.update(objs, frame, labels)
        
        # Visitation should be created
        self.assertIsNotNone(self.visitations.visitation_id)
        self.assertEqual(self.visitations.photo_per_visitation_count, 1)
    
    def test_photo_limit(self):
        """Test that photo count respects limit."""
        labels = {14: "bird"}
        frame = MagicMock()
        frame.shape = (1536, 2048, 3)
        objs = [self.mock_obj]
        
        # Set limit to 2 for testing
        self.visitations.photo_per_visitation_max = 2
        
        # First photo (creates visitation)
        self.visitations.update(objs, frame, labels)
        self.assertEqual(self.visitations.photo_per_visitation_count, 1)
        
        # Second photo
        self.visitations.update(objs, frame, labels)
        self.assertEqual(self.visitations.photo_per_visitation_count, 2)
        
        # Third photo should not increment (at limit)
        # Need to reset started_tracking to avoid timeout
        self.visitations.started_tracking = time.time()
        self.visitations.update(objs, frame, labels)
        self.assertEqual(self.visitations.photo_per_visitation_count, 2, "Photo count should not exceed max")
    
    def test_visitation_reset(self):
        """Test that visitation resets correctly."""
        labels = {14: "bird"}
        frame = MagicMock()
        frame.shape = (1536, 2048, 3)
        objs = [self.mock_obj]
        
        # Create visitation
        self.visitations.update(objs, frame, labels)
        visitation_id = self.visitations.visitation_id
        
        # Reset
        self.visitations.reset()
        
        # Should be reset
        self.assertIsNone(self.visitations.visitation_id)
        self.assertEqual(self.visitations.photo_per_visitation_count, 0)
        self.assertEqual(self.visitations.full_photo_per_visitation_count, 0)
    
    def test_visitation_timeout(self):
        """Test that visitation times out after max seconds."""
        labels = {14: "bird"}
        frame = MagicMock()
        frame.shape = (1536, 2048, 3)
        objs = [self.mock_obj]
        
        # Create visitation
        self.visitations.update(objs, frame, labels)
        self.visitations.vistation_max_seconds = 1.0  # 1 second for testing
        
        # Wait past timeout
        time.sleep(1.1)
        
        # Update without bird (simulates bird leaving)
        self.visitations.update([], frame, labels)
        
        # Should reset (timeout exceeded)
        # Note: Actual behavior depends on implementation
        # This is a placeholder test


class TestVisitation(unittest.TestCase):
    """Test Visitation class."""
    
    def test_visitation_creation(self):
        """Test that visitation is created with UUID."""
        visitation = Visitation()
        self.assertIsNotNone(visitation.id)
    
    def test_visitation_start(self):
        """Test that visitation start time is set."""
        visitation = Visitation()
        visitation.start()
        self.assertIsNotNone(visitation.start_time)
    
    def test_visitation_duration(self):
        """Test that duration is calculated correctly."""
        visitation = Visitation()
        visitation.start()
        time.sleep(0.1)
        visitation.end(time.time())
        duration = visitation.duration()
        self.assertGreater(duration, 0)
        self.assertLess(duration, 1.0)  # Should be around 0.1 seconds


if __name__ == '__main__':
    unittest.main()

