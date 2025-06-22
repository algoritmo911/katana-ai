import unittest
from bot.commands.handler import CommandHandler
from bot.nlp.parser import NLPParser # Used to simulate input to CommandHandler

class TestCommandHandler(unittest.TestCase):

    def setUp(self):
        self.command_handler = CommandHandler()
        self.nlp_parser = NLPParser() # To generate realistic input for handle_command

    def _get_parsed_command(self, command_string: str):
        """Helper to parse a command string using NLPParser."""
        parsed_data = self.nlp_parser.parse_message(command_string)
        if parsed_data["type"] == "command":
            return parsed_data
        self.fail(f"'{command_string}' did not parse as a command.")

    def test_handle_start_command(self):
        parsed_data = self._get_parsed_command("/start")
        response = self.command_handler.handle_command(parsed_data)
        self.assertIn("Hello! I am your friendly bot.", response)

    def test_handle_help_command(self):
        parsed_data = self._get_parsed_command("/help")
        response = self.command_handler.handle_command(parsed_data)
        self.assertIn("Available commands:", response)
        self.assertIn("/start", response)
        self.assertIn("/help", response)
        self.assertIn("/echo", response) # Default echo command

    def test_handle_echo_command_with_args(self):
        text_to_echo = "hello there friend"
        parsed_data = self._get_parsed_command(f"/echo {text_to_echo}")
        response = self.command_handler.handle_command(parsed_data)
        self.assertEqual(response, text_to_echo)

    def test_handle_echo_command_no_args(self):
        parsed_data = self._get_parsed_command("/echo")
        response = self.command_handler.handle_command(parsed_data)
        self.assertEqual(response, "Usage: /echo <text to echo>")

    def test_handle_unknown_command(self):
        parsed_data = self._get_parsed_command("/nonexistentcommand")
        # Ensure the parser actually created a command structure for it
        self.assertEqual(parsed_data["command"], "nonexistentcommand")

        response = self.command_handler.handle_command(parsed_data)
        self.assertEqual(response, "Unknown command: '/nonexistentcommand'. Type /help for a list of commands.")

    def test_register_and_handle_new_command(self):
        def my_custom_command_func(args: list[str]) -> str:
            if args:
                return f"Custom command executed with: {' '.join(args)}"
            return "Custom command executed!"

        self.command_handler.register_command("custom", my_custom_command_func)

        # Test new command is in help
        parsed_help_data = self._get_parsed_command("/help")
        help_response = self.command_handler.handle_command(parsed_help_data)
        self.assertIn("/custom", help_response)

        # Test new command without args
        parsed_custom_data = self._get_parsed_command("/custom")
        response = self.command_handler.handle_command(parsed_custom_data)
        self.assertEqual(response, "Custom command executed!")

        # Test new command with args
        custom_args = "arg1 arg2"
        parsed_custom_with_args_data = self._get_parsed_command(f"/custom {custom_args}")
        response_with_args = self.command_handler.handle_command(parsed_custom_with_args_data)
        self.assertEqual(response_with_args, f"Custom command executed with: {custom_args}")

    def test_handle_command_overwrite_warning(self):
        # This test checks for a print warning, which is harder to assert directly
        # without redirecting stdout. For now, we'll just ensure functionality.
        def original_func(args): return "original"
        def new_func(args): return "new"

        self.command_handler.register_command("testoverwrite", original_func)
        parsed_data_v1 = self._get_parsed_command("/testoverwrite")
        self.assertEqual(self.command_handler.handle_command(parsed_data_v1), "original")

        # print("Overwriting command 'testoverwrite' for testing purposes...") # Manual check
        self.command_handler.register_command("testoverwrite", new_func) # Should print warning
        parsed_data_v2 = self._get_parsed_command("/testoverwrite")
        self.assertEqual(self.command_handler.handle_command(parsed_data_v2), "new")


    def test_handle_command_not_a_command_input(self):
        # Simulate input that NLPParser wouldn't classify as a command
        not_a_command_data = {"type": "message", "raw_text": "hello"}
        response = self.command_handler.handle_command(not_a_command_data)
        self.assertEqual(response, "Error: Not a valid command format.")

    def test_command_execution_exception_handling(self):
        def faulty_command_func(args: list[str]) -> str:
            raise ValueError("Something went wrong in the command")

        self.command_handler.register_command("faulty", faulty_command_func)
        parsed_data = self._get_parsed_command("/faulty")
        response = self.command_handler.handle_command(parsed_data)
        self.assertEqual(response, "An error occurred while executing the command 'faulty'.")

if __name__ == '__main__':
    unittest.main()
