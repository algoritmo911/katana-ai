import unittest
from unittest.mock import Mock
from hydra_observer.reactor.reaction_core import ReactionCore

class TestReactionCore(unittest.TestCase):
    def test_register_and_trigger(self):
        """Tests that a handler is called when an event is triggered."""
        reaction_core = ReactionCore()
        mock_handler = Mock()

        reaction_core.register("test_event", mock_handler)
        reaction_core.trigger("test_event", {"data": "test_data"})

        mock_handler.assert_called_once_with({"data": "test_data"})

    def test_trigger_with_no_handlers(self):
        """Tests that no error occurs when an event is triggered with no handlers."""
        reaction_core = ReactionCore()
        reaction_core.trigger("test_event", {"data": "test_data"})

    def test_multiple_handlers(self):
        """Tests that multiple handlers are called when an event is triggered."""
        reaction_core = ReactionCore()
        mock_handler1 = Mock()
        mock_handler2 = Mock()

        reaction_core.register("test_event", mock_handler1)
        reaction_core.register("test_event", mock_handler2)
        reaction_core.trigger("test_event", {"data": "test_data"})

        mock_handler1.assert_called_once_with({"data": "test_data"})
        mock_handler2.assert_called_once_with({"data": "test_data"})

if __name__ == '__main__':
    unittest.main()
