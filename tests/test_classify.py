"""
Tests for classify.py metadata handling.
Verifies metadata JSONs move with photos instead of being copied and left behind.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classify import move_metadata


class TestMoveMetadata(unittest.TestCase):
    """Test that move_metadata relocates the source JSON with the photo."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="leroy_classify_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_photo(self, photo_id, photo_type):
        src_dir = Path(self.tmp) / "detected" / "2026-08-05" / "visit1"
        src_dir.mkdir(parents=True, exist_ok=True)
        png = src_dir / f"{photo_id}{'_full' if photo_type == 'full' else ''}.png"
        png.touch()
        metadata = {"photo_id": photo_id, "photo_type": photo_type}
        (src_dir / png.name.replace('.png', '.json')).write_text(json.dumps(metadata))
        return png

    def test_moves_metadata_alongside_photo(self):
        png = self._make_photo("abc123", "boxed")
        new_dir = Path(self.tmp) / "classified" / "2026-08-05" / "visit1"
        new_dir.mkdir(parents=True, exist_ok=True)
        new_meta = new_dir / "abc123.json"

        move_metadata(str(png), str(new_meta), {"photo_id": "abc123", "photo_type": "boxed"})

        self.assertTrue(new_meta.exists(), "metadata should be moved to new location")
        self.assertFalse(png.with_suffix('.json').exists(), "source metadata should not remain behind")
        self.assertEqual(json.loads(new_meta.read_text())["photo_id"], "abc123")

    def test_falls_back_to_copy_when_source_missing(self):
        png = self._make_photo("xyz789", "full")
        png.with_suffix('.json').unlink()
        new_dir = Path(self.tmp) / "classified2"
        new_dir.mkdir(parents=True, exist_ok=True)
        new_meta = new_dir / "xyz789_full.json"

        move_metadata(str(png), str(new_meta), {"photo_id": "xyz789", "photo_type": "full"})

        self.assertTrue(new_meta.exists(), "metadata should be written when source is missing")


if __name__ == '__main__':
    unittest.main()
