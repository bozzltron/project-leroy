"""
Tests for photo capture and storage utilities.
"""
import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from photo import has_disk_space, mkdirs


class TestPhotoUtilities(unittest.TestCase):
    """Test photo utility functions."""
    
    @patch('photo.psutil.disk_usage')
    def test_has_disk_space_sufficient(self, mock_disk_usage):
        """Test disk space check when space is available."""
        mock_disk = Mock()
        mock_disk.percent = 80.0  # 80% used, below 95% threshold
        mock_disk_usage.return_value = mock_disk
        
        result = has_disk_space()
        self.assertTrue(result)
    
    @patch('photo.psutil.disk_usage')
    def test_has_disk_space_full(self, mock_disk_usage):
        """Test disk space check when disk is full."""
        mock_disk = Mock()
        mock_disk.percent = 96.0  # 96% used, above 95% threshold
        mock_disk_usage.return_value = mock_disk
        
        result = has_disk_space()
        self.assertFalse(result)
    
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_mkdirs_creates_directory(self, mock_makedirs, mock_exists):
        """Test that mkdirs creates directory when it doesn't exist."""
        mock_exists.return_value = False
        visitation_id = "test-uuid-1234"
        
        result = mkdirs(visitation_id)
        
        # Should create directory
        mock_makedirs.assert_called_once()
        self.assertIn(visitation_id, result)
    
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_mkdirs_skips_existing(self, mock_makedirs, mock_exists):
        """Test that mkdirs doesn't create directory when it exists."""
        mock_exists.return_value = True
        visitation_id = "test-uuid-1234"
        
        result = mkdirs(visitation_id)
        
        # Should not create directory
        mock_makedirs.assert_not_called()
        self.assertIn(visitation_id, result)


if __name__ == '__main__':
    unittest.main()

