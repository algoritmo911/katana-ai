import unittest
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Adjust path to make katana modules importable
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from katana.gestalt.engine import GestaltEngine
from katana.gestalt.events import GestaltEvent

class TestGestaltEngine(unittest.TestCase):

    def test_engine_initialization(self):
        """Test that the engine and its components are initialized."""
        with patch('katana.gestalt.engine.SensorHub') as MockSensorHub, \
             patch('katana.gestalt.engine.SentimentAnalyzer') as MockSentimentAnalyzer, \
             patch('katana.gestalt.engine.GraphMemory') as MockGraphMemory:

            engine = GestaltEngine()

            self.assertIsNotNone(engine)
            MockSensorHub.assert_called_once()
            MockSentimentAnalyzer.assert_called_once()
            MockGraphMemory.assert_called_once()
            # Check that GraphMemory was initialized with the default keywords
            self.assertIn('entity_keywords', MockGraphMemory.call_args[1])
            self.assertIn('katana', MockGraphMemory.call_args[1]['entity_keywords'])

    def test_process_sensor_data(self):
        """Test the full processing pipeline for a single piece of data."""
        with patch('katana.gestalt.engine.SentimentAnalyzer') as MockSentimentAnalyzer, \
             patch('katana.gestalt.engine.GraphMemory') as MockGraphMemory:

            mock_sentiment_analyzer = MockSentimentAnalyzer.return_value
            mock_memory = MockGraphMemory.return_value

            # Re-instantiate engine to use these mocks
            engine = GestaltEngine()
            # Replace the analyzer and memory with our mocks for this test
            engine.sentiment_analyzer = mock_sentiment_analyzer
            engine.memory = mock_memory

            # Arrange
            sensor_id = "test_sensor"
            content = "This is a test message."
            expected_valence = 0.5
            mock_sentiment_analyzer.get_valence.return_value = expected_valence

            # Act
            engine._process_sensor_data(sensor_id, content)

            # Assert
            mock_sentiment_analyzer.get_valence.assert_called_once_with(content)
            mock_memory.add_event.assert_called_once()

            added_event = mock_memory.add_event.call_args[0][0]
            self.assertIsInstance(added_event, GestaltEvent)
            self.assertEqual(added_event.source_id, sensor_id)
            self.assertEqual(added_event.content, content)
            self.assertEqual(added_event.valence, expected_valence)

    def test_setup_default_sensors(self):
        """Test the helper method for setting up sensors."""
        with patch('katana.gestalt.engine.FileSensor') as MockFileSensor:
            engine = GestaltEngine()
            log_file_path = "/var/log/test.log"

            # Act
            engine.setup_default_sensors(log_file_path)

            # Assert
            # Check that a FileSensor was instantiated
            MockFileSensor.assert_called_once()

            # Check the state of the real sensor_hub to confirm registration
            self.assertEqual(len(engine.sensor_hub.sensors), 1)
            registered_sensor = list(engine.sensor_hub.sensors.values())[0]
            self.assertEqual(registered_sensor, MockFileSensor.return_value)

if __name__ == '__main__':
    unittest.main()
