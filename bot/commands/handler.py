from typing import Callable, Dict, List, Any
from bot.nlp.parser import NLPParser # For demonstration purposes

# Define a type alias for command functions
CommandFunction = Callable[[List[str]], str] # Takes list of args, returns response string

class CommandHandler:
    def __init__(self):
        self.commands: Dict[str, CommandFunction] = {}
        self._register_default_commands()

    def _register_default_commands(self):
        """Registers some basic built-in commands."""
        self.register_command("start", self._command_start)
        self.register_command("help", self._command_help)
        self.register_command("echo", self._command_echo) # Example command with args

    def register_command(self, command_name: str, function: CommandFunction):
        """
        Registers a new command.

        Args:
            command_name (str): The name of the command (e.g., "start", "help").
            function (CommandFunction): The function to execute for this command.
                                        It should accept a list of string arguments
                                        and return a string response.
        """
        if command_name in self.commands:
            print(f"Warning: Command '{command_name}' is being overwritten.")
        self.commands[command_name.lower()] = function

    def handle_command(self, parsed_command_data: Dict[str, Any]) -> str:
        """
        Handles a parsed command.

        Args:
            parsed_command_data (Dict[str, Any]): The output from NLPParser
                                                 when a command is detected.
                                                 Expected keys: "command", "args".

        Returns:
            str: The response string from the executed command, or an error message.
        """
        if parsed_command_data.get("type") != "command":
            return "Error: Not a valid command format."

        command_name = parsed_command_data.get("command", "").lower()
        args = parsed_command_data.get("args", [])

        if command_name in self.commands:
            try:
                return self.commands[command_name](args)
            except Exception as e:
                print(f"Error executing command '{command_name}' with args {args}: {e}")
                return f"An error occurred while executing the command '{command_name}'."
        else:
            return f"Unknown command: '/{command_name}'. Type /help for a list of commands."

    # --- Default Command Implementations ---

    def _command_start(self, args: List[str]) -> str:
        """Handles the /start command."""
        # 'args' is available if needed, e.g. /start some_parameter
        return "Hello! I am your friendly bot. Type /help to see what I can do."

    def _command_help(self, args: List[str]) -> str:
        """Handles the /help command."""
        available_commands = [f"/{cmd}" for cmd in self.commands.keys()]
        help_text = "Available commands:\n" + "\n".join(available_commands)
        return help_text

    def _command_echo(self, args: List[str]) -> str:
        """Handles the /echo command. Repeats the arguments given."""
        if not args:
            return "Usage: /echo <text to echo>"
        return " ".join(args)

if __name__ == '__main__':
    # For demonstration, we'll also use the NLPParser
    nlp_parser = NLPParser()
    command_handler = CommandHandler()

    # Example: Register a new custom command
    def custom_greet(args: List[str]) -> str:
        if args:
            return f"Hello, {' '.join(args)}! This is a custom command."
        return "Hello from a custom command! Try /greet [your name]"
    command_handler.register_command("greet", custom_greet)

    # Test cases
    test_inputs = [
        "/start",
        "/help",
        "/echo Hello World, how are you?",
        "/greet Jules",
        "/greet",
        "/unknown_command",
        "This is not a command", # Should be handled by NLPParser differently
        "/echo" # Test echo with no args
    ]

    for text_input in test_inputs:
        print(f"Input: {text_input}")
        parsed_data = nlp_parser.parse_message(text_input)

        response = ""
        if parsed_data["type"] == "command":
            response = command_handler.handle_command(parsed_data)
        elif parsed_data["type"] == "intent":
            response = f"Detected intent: {parsed_data['intent']}"
            if parsed_data['entities']:
                 response += f" with entities: {parsed_data['entities']}"
        else: # message type
            response = f"Received a general message: {parsed_data['raw_text']}"
            if parsed_data['entities']:
                 response += f" with entities: {parsed_data['entities']}"

        print(f"Response: {response}\n")

    # Show updated help
    parsed_help = nlp_parser.parse_message("/help")
    print(f"Input: /help")
    print(f"Response: {command_handler.handle_command(parsed_help)}\n")
