import unittest
import sys
from pathlib import Path

# Adjust path to make katana modules importable
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from katana.gestalt.nlp import EntityExtractor

class TestEntityExtractor(unittest.TestCase):

    def test_entity_extraction(self):
        """Test basic entity extraction."""
        keywords = ['katana', 'error', 'database']
        extractor = EntityExtractor(keywords)
        text = "An error occurred in the Katana application while connecting to the database."

        entities = extractor.extract_entities(text)

        self.assertEqual(entities, {'katana', 'error', 'database'})

    def test_case_insensitivity(self):
        """Test that extraction is case-insensitive."""
        keywords = ['Katana', 'ERROR']
        extractor = EntityExtractor(keywords)
        text = "An Error was found in KATANA."

        entities = extractor.extract_entities(text)

        self.assertEqual(entities, {'katana', 'error'})

    def test_no_matches(self):
        """Test that an empty set is returned when no keywords match."""
        keywords = ['system', 'failure']
        extractor = EntityExtractor(keywords)
        text = "Everything is running smoothly."

        entities = extractor.extract_entities(text)

        self.assertEqual(entities, set())

    def test_word_boundaries(self):
        """Test that keywords are matched as whole words."""
        keywords = ['cat']
        extractor = EntityExtractor(keywords)
        text = "The catalog was updated by concatenation."

        entities = extractor.extract_entities(text)

        self.assertEqual(entities, set())

        text_with_word = "A cat sat on the mat."
        entities_with_word = extractor.extract_entities(text_with_word)
        self.assertEqual(entities_with_word, {'cat'})

    def test_empty_keywords_or_text(self):
        """Test behavior with empty inputs."""
        # No keywords
        extractor = EntityExtractor([])
        text = "Some text with entities."
        self.assertEqual(extractor.extract_entities(text), set())

        # Empty text
        extractor_with_kw = EntityExtractor(['test'])
        self.assertEqual(extractor_with_kw.extract_entities(""), set())

if __name__ == '__main__':
    unittest.main()
