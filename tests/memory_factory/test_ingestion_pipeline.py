import unittest
import time
from unittest.mock import patch, MagicMock

from katana.memory_factory.ingestion_pipeline import IngestionPipeline


class TestIngestionPipeline(unittest.TestCase):

    def setUp(self):
        """Set up for each test."""
        # We patch TruthDetector during the entire test class execution
        # to avoid instantiating the real one and to monitor its calls.
        self.truth_detector_patcher = patch(
            "katana.memory_factory.ingestion_pipeline.TruthDetector"
        )
        self.MockTruthDetector = self.truth_detector_patcher.start()
        self.mock_truth_detector_instance = self.MockTruthDetector.return_value

        self.pipeline = IngestionPipeline()

    def tearDown(self):
        """Tear down after each test."""
        self.pipeline.stop()
        self.truth_detector_patcher.stop()

    def test_initialization(self):
        """Test that the pipeline initializes correctly."""
        self.assertIsNotNone(self.pipeline.data_queue)
        self.assertIsNotNone(self.pipeline.truth_detector)
        self.assertIsNone(self.pipeline._worker_thread)
        # Check that our mock was used for the instance
        self.assertEqual(self.pipeline.truth_detector, self.mock_truth_detector_instance)

    def test_add_to_queue(self):
        """Test adding items to the priority queue."""
        self.pipeline.add_to_queue({"content": "test_high_priority"}, priority=1)
        self.pipeline.add_to_queue({"content": "test_low_priority"}, priority=10)
        self.pipeline.add_to_queue({"content": "test_mid_priority"}, priority=5)

        self.assertEqual(self.pipeline.data_queue.qsize(), 3)

        # Items should come out in order of priority (lower number first)
        p1, d1 = self.pipeline.data_queue.get()
        self.assertEqual(p1, 1)
        self.assertEqual(d1["content"], "test_high_priority")

        p2, d2 = self.pipeline.data_queue.get()
        self.assertEqual(p2, 5)
        self.assertEqual(d2["content"], "test_mid_priority")

        p3, d3 = self.pipeline.data_queue.get()
        self.assertEqual(p3, 10)
        self.assertEqual(d3["content"], "test_low_priority")

    def test_sanitize_content(self):
        """Test the content sanitization logic."""
        raw_content = '<p>This is a TeSt with <b>HTML</b> and UNICODE (éàç).</p>'
        # NFKC normalization standardizes characters but does not transliterate.
        # The correct expectation is that the accents are preserved but standardized.
        expected_content = 'this is a test with html and unicode (éàç).'
        sanitized = self.pipeline.sanitize_content(raw_content)
        self.assertEqual(sanitized, expected_content)

        # Test with non-string
        sanitized_num = self.pipeline.sanitize_content(123)
        self.assertEqual(sanitized_num, "123")

    def test_worker_processing(self):
        """Test the full worker pipeline from queue to TruthDetector."""
        # Add an item to the queue
        test_data = {"content": "Raw <p>Content</p> for analysis"}
        self.pipeline.add_to_queue(test_data, priority=1)

        # Start the worker
        self.pipeline.start()

        # Give the worker a moment to process the single item
        # A short sleep is okay for this kind of test, but for more complex scenarios,
        # one might use threading.Event or other synchronization.
        time.sleep(0.1)

        # Stop the worker to ensure it finishes
        self.pipeline.stop()

        # Check that TruthDetector's analyze method was called exactly once
        self.mock_truth_detector_instance.analyze.assert_called_once()

        # Check the content of what was passed to analyze
        call_args, _ = self.mock_truth_detector_instance.analyze.call_args
        analyzed_data = call_args[0]

        self.assertEqual(analyzed_data["content"], "Raw <p>Content</p> for analysis")
        self.assertEqual(analyzed_data["sanitized_content"], "raw content for analysis")

    def test_start_stop_idempotency(self):
        """Test that start and stop methods can be called multiple times safely."""
        self.pipeline.start()
        self.assertTrue(self.pipeline._worker_thread.is_alive())

        # Calling start again should not create a new thread
        first_thread = self.pipeline._worker_thread
        self.pipeline.start() # This should be a no-op and log a warning
        self.assertIs(self.pipeline._worker_thread, first_thread)

        self.pipeline.stop()
        # The join in stop() should ensure the thread is no longer alive
        self.assertFalse(self.pipeline._worker_thread.is_alive())

        # Calling stop again should do nothing and not raise an error
        self.pipeline.stop()
        self.assertFalse(self.pipeline._worker_thread.is_alive())


if __name__ == "__main__":
    unittest.main()
