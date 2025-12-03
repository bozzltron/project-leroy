"""
Tests for visitation processing functions (visitation.py).
Tests critical processing logic: parsing, multi-species, scientific format.
"""
import unittest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Note: add_padding_to_bbox is in visitations.py, not visitation.py
from visitations import add_padding_to_bbox
from visitation import (
    parse,
    find_species,
    find_all_species,
    create_species_observations,
    get_scientific_name,
    find_best_photo_for_species,
    find_best_photo,
    clarity
)


class TestParse(unittest.TestCase):
    """Test filename parsing function."""
    
    def test_parse_6_fields(self):
        """Test parsing filename with 6 fields."""
        filename = "/var/www/html/classified/2024-01-15/abc123/boxed_2024-01-15_14-30-25_85_american-robin_92.png"
        result = parse(filename)
        
        self.assertEqual(result['species'], "american robin")
        self.assertEqual(result['detection_score'], "85")
        self.assertEqual(result['classification_score'], "92")
        self.assertEqual(result['visitation_id'], "")
        self.assertIsInstance(result['datetime'], datetime)
    
    def test_parse_7_fields(self):
        """Test parsing filename with 7 fields (includes visitation_id)."""
        filename = "/var/www/html/classified/2024-01-15/abc123/boxed_2024-01-15_14-30-25_85_abc123_american-robin_92.png"
        result = parse(filename)
        
        self.assertEqual(result['species'], "american robin")
        self.assertEqual(result['visitation_id'], "abc123")
        self.assertEqual(result['detection_score'], "85")
        self.assertEqual(result['classification_score'], "92")


class TestFindSpecies(unittest.TestCase):
    """Test species finding functions."""
    
    def test_find_species_single(self):
        """Test finding single species."""
        records = [
            {'species': 'american-robin', 'datetime': datetime.now()},
            {'species': 'american-robin', 'datetime': datetime.now()},
        ]
        result = find_species(records)
        self.assertEqual(result, 'american-robin')
    
    def test_find_species_multiple(self):
        """Test finding most common species."""
        records = [
            {'species': 'american-robin', 'datetime': datetime.now()},
            {'species': 'house-finch', 'datetime': datetime.now()},
            {'species': 'house-finch', 'datetime': datetime.now()},
        ]
        result = find_species(records)
        self.assertEqual(result, 'house-finch')  # Most common
    
    def test_find_species_empty(self):
        """Test with empty records."""
        records = []
        result = find_species(records)
        self.assertEqual(result, "")


class TestFindAllSpecies(unittest.TestCase):
    """Test multi-species finding function."""
    
    def test_find_all_species_single(self):
        """Test finding single species with counts."""
        records = [
            {
                'species': 'american-robin',
                'datetime': datetime(2024, 1, 15, 10, 0, 0),
                'classification_score': '85'
            },
            {
                'species': 'american-robin',
                'datetime': datetime(2024, 1, 15, 10, 5, 0),
                'classification_score': '90'
            },
        ]
        result = find_all_species(records)
        
        self.assertEqual(len(result), 1)
        self.assertIn('american-robin', result)
        self.assertEqual(result['american-robin']['count'], 2)
        self.assertEqual(result['american-robin']['first_seen'], datetime(2024, 1, 15, 10, 0, 0))
        self.assertEqual(result['american-robin']['last_seen'], datetime(2024, 1, 15, 10, 5, 0))
        self.assertAlmostEqual(result['american-robin']['avg_confidence'], 0.875, places=2)  # (85+90)/2/100
    
    def test_find_all_species_multiple(self):
        """Test finding multiple species with counts."""
        records = [
            {
                'species': 'american-robin',
                'datetime': datetime(2024, 1, 15, 10, 0, 0),
                'classification_score': '85'
            },
            {
                'species': 'house-finch',
                'datetime': datetime(2024, 1, 15, 10, 2, 0),
                'classification_score': '90'
            },
            {
                'species': 'american-robin',
                'datetime': datetime(2024, 1, 15, 10, 5, 0),
                'classification_score': '88'
            },
        ]
        result = find_all_species(records)
        
        self.assertEqual(len(result), 2)
        self.assertIn('american-robin', result)
        self.assertIn('house-finch', result)
        self.assertEqual(result['american-robin']['count'], 2)
        self.assertEqual(result['house-finch']['count'], 1)


class TestCreateSpeciesObservations(unittest.TestCase):
    """Test scientific format species observations."""
    
    def test_create_species_observations_single(self):
        """Test creating observations for single species."""
        records = [
            {
                'species': 'american-robin',
                'datetime': datetime(2024, 1, 15, 10, 0, 0),
                'classification_score': '85',
                'detection_score': '90',
                'filename': '/var/www/html/classified/2024-01-15/abc123/boxed_2024-01-15_10-00-00_90_american-robin_85.png'
            },
        ]
        
        with patch('visitation.get_scientific_name', return_value='Turdus migratorius'):
            observations = create_species_observations(records)
        
        self.assertEqual(len(observations), 1)
        obs = observations[0]
        self.assertEqual(obs['common_name'], 'american-robin')
        self.assertEqual(obs['scientific_name'], 'Turdus migratorius')
        self.assertEqual(obs['count'], 1)
        self.assertEqual(len(obs['photos']), 1)
        self.assertIn('best_photo', obs)
    
    def test_create_species_observations_multiple(self):
        """Test creating observations for multiple species."""
        records = [
            {
                'species': 'american-robin',
                'datetime': datetime(2024, 1, 15, 10, 0, 0),
                'classification_score': '85',
                'detection_score': '90',
                'filename': '/var/www/html/classified/2024-01-15/abc123/boxed_2024-01-15_10-00-00_90_american-robin_85.png'
            },
            {
                'species': 'house-finch',
                'datetime': datetime(2024, 1, 15, 10, 2, 0),
                'classification_score': '88',
                'detection_score': '92',
                'filename': '/var/www/html/classified/2024-01-15/abc123/boxed_2024-01-15_10-02-00_92_house-finch_88.png'
            },
        ]
        
        with patch('visitation.get_scientific_name', side_effect=['Turdus migratorius', 'Haemorhous mexicanus']):
            observations = create_species_observations(records)
        
        self.assertEqual(len(observations), 2)
        # Should be sorted by count (most common first)
        self.assertEqual(observations[0]['common_name'], 'american-robin')
        self.assertEqual(observations[1]['common_name'], 'house-finch')


class TestGetScientificName(unittest.TestCase):
    """Test scientific name extraction."""
    
    def test_get_scientific_name_from_labels(self):
        """Test extracting scientific name from labels file."""
        # Create temporary labels file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("1 american-robin (Turdus migratorius)\n")
            f.write("2 house-finch (Haemorhous mexicanus)\n")
            labels_path = f.name
        
        try:
            result = get_scientific_name('american-robin', labels_path)
            self.assertEqual(result, 'Turdus migratorius')
        finally:
            os.unlink(labels_path)
    
    def test_get_scientific_name_not_found(self):
        """Test when scientific name not found."""
        result = get_scientific_name('unknown-bird', None)
        self.assertEqual(result, 'Unknown')
    
    def test_get_scientific_name_no_labels_file(self):
        """Test when labels file not provided."""
        result = get_scientific_name('american-robin', None)
        self.assertEqual(result, 'Unknown')


class TestFindBestPhoto(unittest.TestCase):
    """Test best photo selection."""
    
    def test_find_best_photo(self):
        """Test finding best photo from records."""
        records = [
            {
                'filename': '/var/www/html/classified/2024-01-15/abc123/boxed_2024-01-15_10-00-00_90_american-robin_85.png',
                'classification_score': '85',
                'detection_score': '90'
            },
            {
                'filename': '/var/www/html/classified/2024-01-15/abc123/boxed_2024-01-15_10-01-00_92_american-robin_88.png',
                'classification_score': '88',
                'detection_score': '92'
            },
        ]
        
        with patch('visitation.clarity', side_effect=[100, 200]):  # Second photo has higher clarity
            result = find_best_photo(records)
        
        # Should return index of best photo (highest total score)
        # Photo 1: 85 + 90 + 100 = 275
        # Photo 2: 88 + 92 + 200 = 380 (best)
        self.assertEqual(result, 1)


class TestAddPaddingToBbox(unittest.TestCase):
    """Test bbox padding function."""
    
    def test_add_padding_to_bbox(self):
        """Test adding padding to bounding box."""
        bbox = [100, 100, 200, 200]
        result = add_padding_to_bbox(bbox, 1000, 1000, 50)
        
        # Should add 50px padding
        self.assertEqual(result, (50, 50, 250, 250))
    
    def test_add_padding_to_bbox_edge_case(self):
        """Test padding at image edges."""
        bbox = [0, 0, 100, 100]
        result = add_padding_to_bbox(bbox, 500, 500, 50)
        
        # Should not go below 0
        self.assertEqual(result[0], 0)
        self.assertEqual(result[1], 0)
        # Should not exceed image bounds
        self.assertLessEqual(result[2], 500)
        self.assertLessEqual(result[3], 500)


if __name__ == '__main__':
    unittest.main()

