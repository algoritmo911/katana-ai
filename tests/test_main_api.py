import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

# Import the app and other objects from main
from main import app, VALID_API_KEY
from katana.memory_factory.ingestion_pipeline import IngestionPipeline
from logging_config import setup_ingestion_backup_logger
import main as main_app


class TestMainAPI(unittest.TestCase):

    def setUp(self):
        """
        Set up the test client and mock dependencies for each test.
        Manually initialize instances that are normally created in the startup event.
        """
        # Manually set up the instances because TestClient does not run startup events.
        main_app.ingestion_pipeline_instance = IngestionPipeline()
        main_app.ingestion_backup_logger = setup_ingestion_backup_logger()

        # Stop the worker thread that is started by the IngestionPipeline constructor
        # so it doesn't interfere with the endpoint tests.
        if main_app.ingestion_pipeline_instance:
            main_app.ingestion_pipeline_instance.stop()

        self.client = TestClient(app)

        # Now that the instances exist, we can patch their methods.
        self.ingestion_pipeline_patcher = patch(
            "main.ingestion_pipeline_instance.add_to_queue"
        )
        self.mock_add_to_queue = self.ingestion_pipeline_patcher.start()

        self.backup_logger_patcher = patch("main.ingestion_backup_logger.info")
        self.mock_backup_logger_info = self.backup_logger_patcher.start()

    def tearDown(self):
        """Stop the patchers and clean up instances."""
        main_app.ingestion_pipeline_instance.stop()
        self.ingestion_pipeline_patcher.stop()
        self.backup_logger_patcher.stop()
        main_app.ingestion_pipeline_instance = None
        main_app.ingestion_backup_logger = None


    def test_ingest_success(self):
        """Test a successful data ingestion call with a valid API key."""
        headers = {"X-API-KEY": VALID_API_KEY}
        payload = {"content": "This is a test.", "priority": 1, "source": "test-suite"}

        response = self.client.post("/ingest", headers=headers, json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "message": "Data received and queued for processing."},
        )
        self.mock_backup_logger_info.assert_called_once_with(
            '{"content":"This is a test.","priority":1,"source":"test-suite"}'
        )
        self.mock_add_to_queue.assert_called_once_with(
            {"content": "This is a test.", "priority": 1, "source": "test-suite"},
            priority=1,
        )

    def test_ingest_missing_api_key(self):
        """Test that a request with a missing API key header is rejected."""
        payload = {"content": "This is a test."}
        response = self.client.post("/ingest", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_ingest_invalid_api_key(self):
        """Test that a request with an invalid API key is rejected."""
        headers = {"X-API-KEY": "this-is-a-wrong-key"}
        payload = {"content": "This is a test."}
        response = self.client.post("/ingest", headers=headers, json=payload)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid API Key"})
        self.mock_backup_logger_info.assert_not_called()
        self.mock_add_to_queue.assert_not_called()

    def test_health_endpoint(self):
        """Test the /health endpoint."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "OK", "message": "API is healthy."})

    def test_status_endpoint(self):
        """Test the /status endpoint for a successful response."""
        response = self.client.get("/status")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application_status", response.json())


if __name__ == "__main__":
    unittest.main()
