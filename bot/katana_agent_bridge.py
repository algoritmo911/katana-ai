import logging
import os # For path joining if needed, though setup_logger might handle it
from pathlib import Path

# Ensure katana_core.katana and its execute_core_command is discoverable
# This might require adjustments to PYTHONPATH if running from different locations,
# but for a typical project structure, this relative import should work if 'katana_core'
# and 'bot' are sibling directories or 'katana_core' is installed/discoverable.
# Assuming the project root is in PYTHONPATH.
from katana_core.katana import execute_core_command
from katana.utils.logging_config import setup_logger

# Logger setup as per user instruction for "logs/bridge.log" (implies root logs directory)
# setup_logger will create parent directories if they don't exist.
BRIDGE_LOG_FILE_PATH = "logs/bridge.log"
logger = setup_logger("KatanaAgentBridge", BRIDGE_LOG_FILE_PATH, level=logging.DEBUG)


async def execute(command: str, args: list = None) -> dict:
    """
    Asynchronously executes a command via KatanaCore and returns the result.
    Args:
        command: The base command to execute.
        args: A list of arguments for the command.
    Returns:
        A dictionary containing stdout, stderr, and return code.
    """
    if args is None:
        args = []

    # Construct the full command string. Ensure proper spacing and quoting if necessary,
    # though shell=True in execute_core_command handles much of this.
    # For simplicity, just joining with spaces.
    full_command_str_parts = [command] + [str(arg) for arg in args]
    full_command_str = " ".join(full_command_str_parts)

    try:
        logger.info(
            f"Executing command via bridge: '{full_command_str}'",
            extra={"command": command, "command_args": args, "full_command": full_command_str}
        )

        # execute_core_command is synchronous, so it will block here.
        # If true async execution of subprocesses is needed in the future,
        # execute_core_command would need to use asyncio.create_subprocess_shell.
        result = execute_core_command(full_command_str)

        stdout = result.get("stdout", "").strip()
        stderr = result.get("stderr", "").strip()
        code = result.get("code", -1)

        if code == 0:
            logger.info(f"Command '{full_command_str}' executed successfully. Stdout: '{stdout[:100]}...'", extra={"full_command": full_command_str, "code": code, "stdout_preview": stdout[:100]})
        else:
            logger.warning(
                f"Command '{full_command_str}' failed with code {code}. Stderr: '{stderr[:100]}...'",
                 extra={"full_command": full_command_str, "code": code, "stderr_preview": stderr[:100], "stdout_preview": stdout[:100]}
            )

        return {
            "stdout": stdout,
            "stderr": stderr,
            "code": code
        }
    except Exception as e:
        logger.exception(f"Bridge error during command execution: '{full_command_str}'", extra={"full_command": full_command_str, "error": str(e)})
        return {
            "stdout": "",
            "stderr": f"Bridge execution error: {str(e)}",
            "code": -1 # Indicate failure due to bridge exception
        }

if __name__ == '__main__':
    # Example usage (requires asyncio event loop to run async function)
    import asyncio

    async def main():
        # Test with a safe command like 'echo'
        logger.info("Starting bridge example execution...")

        # Example 1: Successful command
        result_echo = await execute("echo", ["Hello", "from", "bridge"])
        print(f"Echo Result: {result_echo}")
        logger.info(f"Echo test completed. Result: {result_echo}")

        # Example 2: Command that might produce stderr or non-zero exit code
        # (Use a command that exists and is safe, e.g., 'ls /nonexistentpath' or 'false')
        result_fail = await execute("ls", ["/nonexistentpath"]) # ls on a non-existent path
        print(f"Fail Example Result (ls /nonexistentpath): {result_fail}")
        logger.info(f"Fail test (ls) completed. Result: {result_fail}")

        result_false = await execute("false") # 'false' command typically exits with 1
        print(f"Fail Example Result (false): {result_false}")
        logger.info(f"Fail test (false) completed. Result: {result_false}")

        # Example 3: Non-existent command (handled by execute_core_command's shell)
        # The shell might return a specific error code (e.g., 127)
        result_bad_cmd = await execute("thiscommandshouldnotexist123")
        print(f"Bad Command Result: {result_bad_cmd}")
        logger.info(f"Bad command test completed. Result: {result_bad_cmd}")

    if os.name == 'nt': # For Windows compatibility of asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
