import unittest
from datetime import datetime, timedelta
from src.katana_core.predictor import Predictor
from src.memory.memory_manager import MemoryManager
import numpy as np
from unittest.mock import MagicMock


class TestPredictor(unittest.TestCase):

    def setUp(self):
        self.memory_manager = MagicMock(spec=MemoryManager)
        self.predictor = Predictor(memory_manager=self.memory_manager)
        self.timestamps = [datetime.now() - timedelta(days=i) for i in range(100)]
        self.data = [i + np.random.random() * 10 for i in range(100)]

    def test_ingest_data(self):
        self.predictor.ingest(self.data, self.timestamps)
        self.assertIsNotNone(self.predictor.series)
        self.assertEqual(len(self.predictor.series), 100)

    def test_predict_arima(self):
        self.predictor.ingest(self.data, self.timestamps)
        predictions = self.predictor.predict(steps=10)
        self.assertEqual(len(predictions), 10)

    def test_predict_prophet(self):
        self.predictor.model_name = 'prophet'
        self.predictor.ingest(self.data, self.timestamps)
        predictions = self.predictor.predict(steps=10)
        self.assertEqual(len(predictions), 10)

    def test_detect_anomalies(self):
        self.predictor.ingest(self.data, self.timestamps)
        # Test with a low threshold to ensure anomaly detection
        is_anomaly = self.predictor.detect_anomalies(threshold=0.1)
        self.assertTrue(is_anomaly)

        # Test with a high threshold
        is_anomaly = self.predictor.detect_anomalies(threshold=100)
        self.assertFalse(is_anomaly)

    def test_ingest_with_missing_values(self):
        data_with_nan = self.data.copy()
        data_with_nan[5] = np.nan
        with self.assertRaises(ValueError):
            self.predictor.ingest(data_with_nan, self.timestamps)

    def test_fetch_data_from_memory(self):
        chat_id = "test_chat"
        history = [
            {'timestamp': (datetime.now() - timedelta(days=i)).isoformat(), 'content': 'a' * (i+1)}
            for i in range(10)
        ]
        self.memory_manager.get_history.return_value = history

        data, timestamps = self.predictor.fetch_data_from_memory(chat_id)

        self.assertEqual(len(data), 10)
        self.assertEqual(len(timestamps), 10)

    def test_fetch_data_from_memory_no_history(self):
        chat_id = "test_chat_no_history"
        self.memory_manager.get_history.return_value = []

        with self.assertRaises(ValueError):
            self.predictor.fetch_data_from_memory(chat_id)


if __name__ == '__main__':
    unittest.main()
