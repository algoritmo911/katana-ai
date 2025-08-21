import unittest
import sys
from pathlib import Path

# Adjust path to make katana modules importable
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from katana.gestalt.emotions import SentimentAnalyzer

class TestSentimentAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = SentimentAnalyzer()

    def test_analyzer_initialization(self):
        """Test that the underlying VADER analyzer is initialized."""
        self.assertIsNotNone(self.analyzer.analyzer)

    def test_positive_valence(self):
        """Test a clearly positive sentence."""
        text = "This is a wonderful, amazing, and fantastic day!"
        valence = self.analyzer.get_valence(text)
        self.assertIsNotNone(valence)
        self.assertGreater(valence, 0.5) # Expect a strong positive score

    def test_negative_valence(self):
        """Test a clearly negative sentence."""
        text = "This is a horrible, terrible, and dreadful experience."
        valence = self.analyzer.get_valence(text)
        self.assertIsNotNone(valence)
        self.assertLess(valence, -0.5) # Expect a strong negative score

    def test_neutral_valence(self):
        """Test a neutral sentence."""
        text = "The cat is on the table."
        valence = self.analyzer.get_valence(text)
        self.assertIsNotNone(valence)
        # Neutral text might not be exactly 0.0, but should be close.
        self.assertAlmostEqual(valence, 0.0, delta=0.2)

    def test_mixed_valence(self):
        """Test a sentence with mixed sentiment."""
        text = "The movie was great, but the ending was terrible."
        valence = self.analyzer.get_valence(text)
        self.assertIsNotNone(valence)
        # The score should be negative due to the contrastive conjunction 'but'.
        self.assertLess(valence, 0.0)

    def test_empty_string(self):
        """Test that an empty string returns a neutral score."""
        text = ""
        valence = self.analyzer.get_valence(text)
        self.assertEqual(valence, 0.0)

    def test_non_string_input(self):
        """Test that non-string input returns a neutral score."""
        text = 12345
        valence = self.analyzer.get_valence(text)
        self.assertEqual(valence, 0.0)

if __name__ == '__main__':
    unittest.main()
