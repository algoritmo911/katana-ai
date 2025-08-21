import sys
import unittest
from unittest.mock import patch, MagicMock, call
import time
import threading

# Mock the telegram_bot module BEFORE it's imported by the orchestrator.
# This prevents the real module from being loaded, which would raise an error
# due to the missing Telegram token environment variable.
mock_telegram_bot = MagicMock()
sys.modules['bot.katana_bot'] = MagicMock()
sys.modules['bot.katana_bot'].bot = mock_telegram_bot

# We need to make sure the orchestrator module is importable
# This might require adjusting sys.path if tests are run from the root directory
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from katana.self_heal.orchestrator import SelfHealingOrchestrator


class TestSelfHealingOrchestrator(unittest.TestCase):

    def setUp(self):
        """Set up a default config for the orchestrator for each test."""
        self.config = {
            "log_file_path": "/tmp/test.log",
            "service_name": "test-service",
            "check_interval_seconds": 1,
            "error_threshold": 5,
            "notification_chat_id": "12345",
        }

    @patch('katana.self_heal.orchestrator.diagnostics.analyze_logs')
    def test_initialization(self, mock_analyze_logs):
        """Test that the orchestrator initializes correctly."""
        orchestrator = SelfHealingOrchestrator(self.config)
        self.assertEqual(orchestrator.config, self.config)
        self.assertFalse(orchestrator.is_running)
        self.assertIsNone(orchestrator.thread)

    @patch('katana.self_heal.orchestrator.patcher.restart_service')
    @patch('katana.self_heal.orchestrator.diagnostics.analyze_logs')
    def test_no_action_when_errors_below_threshold(self, mock_analyze_logs, mock_restart_service):
        """Test that no action is taken if error count is below the threshold."""
        # Arrange: analyze_logs returns 4 errors, which is less than the threshold of 5
        mock_analyze_logs.return_value = (["error"] * 4, "Found 4 errors.")

        orchestrator = SelfHealingOrchestrator(self.config)

        # Act
        orchestrator._perform_health_check()

        # Assert
        mock_analyze_logs.assert_called_once_with(self.config["log_file_path"])
        mock_restart_service.assert_not_called()

    @patch('katana.self_heal.orchestrator.SelfHealingOrchestrator._send_notification')
    @patch('katana.self_heal.orchestrator.patcher.restart_service')
    @patch('katana.self_heal.orchestrator.diagnostics.analyze_logs')
    def test_action_triggered_when_errors_above_threshold(self, mock_analyze_logs, mock_restart_service, mock_send_notification):
        """Test that a restart is triggered if error count exceeds the threshold."""
        # Arrange: analyze_logs returns 6 errors, which is more than the threshold of 5
        mock_analyze_logs.return_value = (["error"] * 6, "Found 6 errors.")
        mock_restart_service.return_value = (True, "Service restarted.")

        orchestrator = SelfHealingOrchestrator(self.config)

        # Act
        orchestrator._perform_health_check()

        # Assert
        mock_analyze_logs.assert_called_once_with(self.config["log_file_path"])
        mock_restart_service.assert_called_once_with(self.config["service_name"])
        mock_send_notification.assert_called_once()
        self.assertIn("restarted successfully", mock_send_notification.call_args[0][0])

    @patch('katana.self_heal.orchestrator.SelfHealingOrchestrator._send_notification')
    @patch('katana.self_heal.orchestrator.patcher.restart_service')
    @patch('katana.self_heal.orchestrator.diagnostics.analyze_logs')
    def test_failed_restart_sends_failure_notification(self, mock_analyze_logs, mock_restart_service, mock_send_notification):
        """Test that a failure notification is sent if the restart fails."""
        # Arrange: analyze_logs returns 6 errors
        mock_analyze_logs.return_value = (["error"] * 6, "Found 6 errors.")
        # Arrange: patcher returns a failure
        mock_restart_service.return_value = (False, "Failed to restart.")

        orchestrator = SelfHealingOrchestrator(self.config)

        # Act
        orchestrator._perform_health_check()

        # Assert
        mock_restart_service.assert_called_once_with(self.config["service_name"])
        mock_send_notification.assert_called_once()
        self.assertIn("Failed to restart", mock_send_notification.call_args[0][0])

    @patch('time.sleep', return_value=None)
    @patch('katana.self_heal.orchestrator.diagnostics.analyze_logs')
    def test_start_and_stop_thread(self, mock_analyze_logs, mock_sleep):
        """Test that the monitoring thread starts and stops correctly."""
        # Arrange
        orchestrator = SelfHealingOrchestrator(self.config)

        # This side effect will run once, then we'll stop the loop from the test
        mock_analyze_logs.return_value = ([], "No errors.")

        # Act
        orchestrator.start()
        self.assertTrue(orchestrator.is_running)
        self.assertTrue(orchestrator.thread.is_alive())

        # Give the thread time to run one loop cycle
        time.sleep(0.1)

        # Stop the orchestrator from the main thread
        orchestrator.stop()

        # Assert
        self.assertFalse(orchestrator.is_running)
        # The join in stop() ensures the thread is no longer alive
        self.assertFalse(orchestrator.thread.is_alive())
        mock_analyze_logs.assert_called()
        mock_analyze_logs.assert_called()


if __name__ == '__main__':
    unittest.main()
