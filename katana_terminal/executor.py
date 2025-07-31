import subprocess
from dataclasses import dataclass
from .utils import is_dangerous_command

@dataclass
class CommandResult:
    """
    Data class to hold the result of a shell command execution.
    """
    stdout: str
    stderr: str
    return_code: int

class ShellExecutor:
    """
    Executes shell commands in a secure way.
    """
    def execute(self, command: str) -> CommandResult:
        """
        Executes a given shell command after checking if it's dangerous.

        Args:
            command: The command to execute.

        Returns:
            A CommandResult object with stdout, stderr, and return code.
        """
        if not command:
            return CommandResult(stdout="", stderr="Empty command.", return_code=1)

        if is_dangerous_command(command):
            return CommandResult(stdout="", stderr=f"'{command}' is a dangerous command and was not executed.", return_code=1)

        try:
            process = subprocess.run(
                command,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
            )
            return CommandResult(
                stdout=process.stdout.strip(),
                stderr=process.stderr.strip(),
                return_code=process.returncode,
            )
        except Exception as e:
            return CommandResult(stdout="", stderr=f"An error occurred: {e}", return_code=1)
