import pytest
import asyncio # Required for pytest.mark.asyncio with older versions or certain setups
import sys
from pathlib import Path

# Add parent directory of 'bot' to sys.path to allow direct import of bot.katana_agent_bridge
# This assumes 'tests' is at the project root, and 'bot' is also at the project root.
# Adjust if your project structure is different.
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from bot.katana_agent_bridge import execute

@pytest.mark.asyncio
async def test_execute_basic_command():
    """Tests executing a basic 'echo' command via the bridge."""
    command = "echo"
    args = ["Katana"]

    # Expected behavior of execute_core_command (mocked by bridge if it were more complex)
    # Here we are testing the bridge's call to the real execute_core_command.
    result = await execute(command, args)

    assert result["stdout"] == "Katana"
    assert result["stderr"] == "" # Expect empty stderr for a successful echo
    assert result["code"] == 0

@pytest.mark.asyncio
async def test_execute_command_with_error_output():
    """Tests a command that produces stderr output."""
    # Using a command that reliably prints to stderr and has a known exit code.
    # Example: 'ls' a non-existent file. The exact stderr message can be OS/locale dependent.
    # For more robust testing, one might create a tiny script that prints to stderr.
    # Let's use a command that should fail and print to stderr using Python.
    py_script_content = "import sys; sys.stderr.write('TestStderrPython\\n'); sys.exit(1)"
    command = sys.executable # Path to current python interpreter
    # Args for "python -c SCRIPT_CONTENT" where SCRIPT_CONTENT is passed as a single arg to -c
    # The bridge joins command and args with spaces. To make py_script_content a single argument
    # for the shell (when shell=True is used by execute_core_command), it needs to be quoted.
    args = ["-c", f'"{py_script_content}"'] # Wrap the script content in double quotes for the shell

    result = await execute(command, args)

    # stderr from python -c "import sys; sys.stderr.write('TestStderrPython\n')
    # will be "TestStderrPython\n". The bridge strips it to "TestStderrPython".
    assert result["stderr"] == "TestStderrPython"
    assert result["code"] == 1

@pytest.mark.asyncio
async def test_execute_non_existent_command():
    """Tests executing a command that does not exist."""
    command = "commandthatshouldnotexist123abc"
    args = []

    result = await execute(command, args)

    # Behavior of non-existent command can vary.
    # `shell=True` in `execute_core_command` means the shell handles it.
    # Often, the shell prints an error to stderr and returns a specific code (e.g., 127).
    assert result["stderr"] != "" # Expect some error message
    assert result["code"] != 0    # Expect a non-zero exit code (e.g. 127 for command not found)

@pytest.mark.asyncio
async def test_execute_no_args():
    """Tests executing a command with no arguments."""
    command = "echo"
    # No args explicitly passed, should default to args=None in bridge `execute`

    result = await execute(command)

    # 'echo' with no arguments usually prints a newline.
    assert result["stdout"] == "" # Echo with no args on many systems prints just a newline, which strip() removes.
    assert result["stderr"] == ""
    assert result["code"] == 0

@pytest.mark.asyncio
async def test_execute_command_with_empty_args_list():
    """Tests executing a command with an empty list of arguments."""
    command = "echo"
    args = []

    result = await execute(command, args)

    assert result["stdout"] == "" # Similar to no args
    assert result["stderr"] == ""
    assert result["code"] == 0

# Note: To run these tests, navigate to the project root directory (the one containing 'tests' and 'bot')
# and run the command: pytest
# Ensure that katana_core/katana.py and bot/katana_agent_bridge.py are correctly implemented
# and that the `setup_logger` in the bridge does not cause issues during test collection/execution
# (e.g., by trying to create log files in restricted places if paths are not handled carefully).
# The logger in the bridge is set up when the module is imported.
# For tests, it might be preferable to mock out the logger or `setup_logger` itself
# if its side effects (like file creation) are undesirable during unit testing.
# However, for this step, we are creating the test as specified.
