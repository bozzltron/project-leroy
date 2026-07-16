"""
Tests for active learning module.
Tests categorization and filtering logic.
"""
import unittest
from unittest.mock import Mock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from active_learning import ActiveLearningCollector


class TestActiveLearningCollector(unittest.TestCase):
    """Test ActiveLearningCollector functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.collector = ActiveLearningCollector(base_dir="test_storage/active_learning")
        self.mock_obj = Mock()
        self.mock_obj.id = 14  # COCO bird class ID
        self.mock_obj.score = 0.85
    
    def test_non_bird_classes_list(self):
        """Test that non-bird classes are defined."""
        self.assertIn('cat', self.collector.non_bird_classes)
        self.assertIn('dog', self.collector.non_bird_classes)
        self.assertEqual(len(self.collector.non_bird_classes), 2)
    
    def test_stats_tracking(self):
        """Test that statistics are tracked."""
        stats = self.collector.get_stats()
        self.assertIn('unknown_birds', stats)
        self.assertIn('non_birds', stats)
        self.assertIn('low_confidence', stats)
    
    def test_stats_reset(self):
        """Test that statistics can be reset."""
        # Simulate some collections
        self.collector.stats['non_birds'] = 5
        self.collector.reset_stats()
        stats = self.collector.get_stats()
        self.assertEqual(stats['non_birds'], 0)


if __name__ == '__main__':
    unittest.main()

