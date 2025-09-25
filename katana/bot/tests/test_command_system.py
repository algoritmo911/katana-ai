import unittest
from unittest.mock import patch, MagicMock
from katana.bot.commands import (
    load_commands,
    get_all_commands,
    register_command,
    command_registry,
)


class TestCommandSystem(unittest.TestCase):
    def setUp(self):
        """Reset the command registry before each test to ensure isolation."""
        command_registry.clear()

    @patch("pkgutil.walk_packages")
    @patch("importlib.import_module")
    def test_load_commands(self, mock_import_module, mock_walk_packages):
        """
        Tests that load_commands() calls import_module for each module found.
        """
        # Mock walk_packages to simulate finding command modules
        mock_walk_packages.return_value = [
            (None, "katana.bot.commands.start", False),
            (None, "katana.bot.commands.help", False),
        ]

        # Reset mock just in case it was called during test setup
        mock_import_module.reset_mock()

        # Call the function to test
        load_commands()

        # Assert that import_module was called for each discovered module
        self.assertEqual(mock_import_module.call_count, 2)
        mock_import_module.assert_any_call("katana.bot.commands.start")
        mock_import_module.assert_any_call("katana.bot.commands.help")

    def test_get_all_commands(self):
        """
        Tests that get_all_commands() returns the current state of the registry.
        """
        # Manually add items to the registry
        command_registry["test1"] = "handler1"
        command_registry["test2"] = "handler2"

        # Call the function to test
        all_commands = get_all_commands()

        # Assert that the returned dictionary is correct
        self.assertEqual(len(all_commands), 2)
        self.assertEqual(all_commands, {"test1": "handler1", "test2": "handler2"})

    def test_command_registration(self):
        """
        Tests that the @register_command decorator correctly adds a
        command handler to the registry. This test is more direct and
        reliable than testing through module imports.
        """
        # Ensure the registry is empty
        self.assertEqual(len(get_all_commands()), 0)

        # Define and decorate a dummy command handler
        @register_command("my_test_command")
        def my_dummy_handler(update, context):
            pass

        # Check that the command is now in the registry
        all_commands = get_all_commands()
        self.assertIn("my_test_command", all_commands)
        self.assertIs(all_commands["my_test_command"], my_dummy_handler)
        self.assertEqual(len(all_commands), 1)


if __name__ == "__main__":
    unittest.main()