import re
from datetime import datetime

# A set of commands that are considered dangerous and should not be executed.
# This is a basic security measure.
DANGEROUS_COMMANDS = {
    'rm -rf',
    'sudo',
    'shutdown',
    'reboot',
    'mkfs',
    'dd',
    ':(){:|:&};:',  # Fork bomb
}

def is_dangerous_command(command: str) -> bool:
    """
    Checks if a command is in the list of dangerous commands.
    It performs a simple check and can be expanded for more complex patterns.

    Args:
        command: The command string to check.

    Returns:
        True if the command is considered dangerous, False otherwise.
    """
    # Normalize the command to handle extra whitespace
    normalized_command = ' '.join(command.strip().split())

    # Check for exact matches or if the command starts with a dangerous prefix
    for dangerous_cmd in DANGEROUS_COMMANDS:
        if normalized_command.startswith(dangerous_cmd):
            return True

    return False

def get_current_time() -> str:
    """
    Returns the current time in a user-friendly format.

    Returns:
        A string representing the current time.
    """
    return datetime.now().strftime("%I:%M %p")

# Placeholder for future NLP/parsing utilities
def parse_command(text: str):
    """
    A placeholder for more advanced command parsing.
    """
    pass
