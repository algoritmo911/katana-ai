import unittest
from unittest.mock import MagicMock, patch, mock_open

from bot_components.handlers.genesis_handler import handle_genesis

class TestGenesisHandler(unittest.TestCase):

    def setUp(self):
        self.mock_bot = MagicMock()
        self.mock_message = MagicMock()
        self.sample_blueprint_yaml = """
name: "Test Agent"
purpose: "A test agent for unit testing."
dependencies:
  - "os"
methods:
  - name: "do_something"
    description: "Does something."
    inputs:
      input_a: "A string."
    outputs: "An integer."
"""
        self.command_data = {
            "type": "genesis",
            "module": "factory",
            "args": {"blueprint": self.sample_blueprint_yaml},
            "id": "gen_test_001"
        }

    @patch("bot_components.handlers.genesis_handler.Path")
    @patch("bot_components.handlers.genesis_handler.open", new_callable=mock_open)
    @patch("bot_components.handlers.genesis_handler.subprocess.run")
    def test_handle_genesis_success(self, mock_subprocess_run, mock_open_func, mock_path):
        # Arrange
        # Mocking the QC tools to return success
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="")

        # Act
        handle_genesis(self.command_data, self.mock_message, self.mock_bot)

        # Assert
        # Check that the file was created
        mock_path.assert_called_with("src/agents")
        mock_path.return_value.mkdir.assert_called_once_with(parents=True, exist_ok=True)

        expected_filepath = mock_path.return_value / "test_agent.py"
        mock_open_func.assert_called_once_with(expected_filepath, "w", encoding="utf-8")

        # Check that black and flake8 were called
        self.assertEqual(mock_subprocess_run.call_count, 2)
        mock_subprocess_run.assert_any_call(
            ["black", str(expected_filepath)], capture_output=True, text=True
        )
        mock_subprocess_run.assert_any_call(
            ["flake8", str(expected_filepath)], capture_output=True, text=True
        )

        # Check that the bot replied
        self.mock_bot.reply_to.assert_called_once()
        reply_text = self.mock_bot.reply_to.call_args[0][1]
        self.assertIn("✅ Genesis complete.", reply_text)
        self.assertIn("✅ `black` formatting successful", reply_text)
        self.assertIn("✅ `flake8` linting successful", reply_text)

if __name__ == '__main__':
    unittest.main()
