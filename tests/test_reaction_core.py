import unittest
from unittest.mock import Mock, patch
from hydra_observer.reactor.reaction_core import ReactionCore
from hydra_observer.reactor.handlers import handle_high_cpu, handle_command_flood, handle_agent_unresponsive, handle_latency_spike

class TestReactionCore(unittest.TestCase):
    def setUp(self):
        """Set up a new ReactionCore for each test."""
        self.reaction_core = ReactionCore()

    def test_register_and_trigger(self):
        """Tests that a handler is called when an event is triggered."""
        mock_handler = Mock()
        self.reaction_core.register("test_event", mock_handler)
        self.reaction_core.trigger("test_event", {"data": "test_data"})
        mock_handler.assert_called_once_with({"data": "test_data"})

    def test_trigger_with_no_handlers(self):
        """Tests that no error occurs when an event is triggered with no handlers."""
        # This test implicitly checks that no exception is raised
        self.reaction_core.trigger("test_event", {"data": "test_data"})

    def test_multiple_handlers(self):
        """Tests that multiple handlers are called when an event is triggered."""
        mock_handler1 = Mock()
        mock_handler2 = Mock()
        self.reaction_core.register("test_event", mock_handler1)
        self.reaction_core.register("test_event", mock_handler2)
        self.reaction_core.trigger("test_event", {"data": "test_data"})
        mock_handler1.assert_called_once_with({"data": "test_data"})
        mock_handler2.assert_called_once_with({"data": "test_data"})

    @patch('hydra_observer.reactor.handlers.logging')
    def test_handle_high_cpu(self, mock_logging):
        """Tests the high CPU handler."""
        handle_high_cpu({"cpu_percent": 95})
        mock_logging.warning.assert_called_with("High CPU usage detected: 95%")

    @patch('hydra_observer.reactor.handlers.logging')
    def test_handle_command_flood(self, mock_logging):
        """Tests the command flood handler."""
        handle_command_flood({})
        mock_logging.warning.assert_called_with("Command flood detected. Throttling commands.")

    @patch('hydra_observer.reactor.handlers.logging')
    def test_handle_agent_unresponsive(self, mock_logging):
        """Tests the agent unresponsive handler."""
        handle_agent_unresponsive({"agent_id": "test_agent"})
        mock_logging.error.assert_called_with("Agent test_agent is unresponsive. Attempting to restart.")

    @patch('hydra_observer.reactor.handlers.logging')
    def test_handle_latency_spike(self, mock_logging):
        """Tests the latency spike handler."""
        handle_latency_spike({"latency_ms": 1000})
        mock_logging.warning.assert_called_with("Latency spike detected: 1000ms")

if __name__ == '__main__':
    unittest.main()
