# src/tools/rclone_sync.py
import subprocess
import os
from typing import Optional, Tuple

def _find_rclone_executable() -> Optional[str]:
    """Tries to find the rclone executable in common locations or PATH."""
    # Common paths (can be expanded)
    common_paths = [
        "/usr/bin/rclone",
        "/usr/local/bin/rclone",
        # Add Windows paths if relevant, though subprocess might handle .exe automatically on Windows if in PATH
    ]
    for path in common_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path

    # Check if rclone is in PATH
    try:
        result = subprocess.run(["which", "rclone"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError: # 'which' command not found (e.g. on minimal systems or Windows)
        pass # Fall through to trying 'rclone' directly

    # Try running 'rclone version' directly, assuming it's in PATH
    try:
        subprocess.run(["rclone", "version"], capture_output=True, check=True)
        return "rclone" # If it runs, it's in PATH
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


RCLONE_EXE = _find_rclone_executable()

def is_rclone_available() -> bool:
    """Checks if rclone is available and executable."""
    return RCLONE_EXE is not None

def sync_data_with_rclone(source: str, destination: str, rclone_config_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Synchronizes data from source to destination using rclone.

    Args:
        source: The source path (local or rclone remote:path).
        destination: The destination path (local or rclone remote:path).
        rclone_config_path: Optional path to a specific rclone.conf file.

    Returns:
        A tuple (success: bool, output_message: str).
    """
    if not is_rclone_available():
        msg = "rclone executable not found. Please install rclone and ensure it's in your PATH."
        print(f"[RcloneSync] ERROR: {msg}")
        return False, msg

    command = [RCLONE_EXE, "sync", source, destination, "--verbose"]

    if rclone_config_path:
        command.extend(["--config", rclone_config_path])

    print(f"[RcloneSync] Executing command: {' '.join(command)}")

    try:
        # Using subprocess.PIPE for stdout and stderr to capture output
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate() # Wait for command to complete

        if process.returncode == 0:
            success_msg = f"Rclone sync successful from '{source}' to '{destination}'."
            print(f"[RcloneSync] {success_msg}")
            # Combine stdout and stderr for the full log, as rclone often uses stderr for verbose info
            return True, f"{success_msg}\nOutput:\n{stdout}\n{stderr}"
        else:
            error_msg = f"Rclone sync failed with return code {process.returncode}."
            print(f"[RcloneSync] ERROR: {error_msg}")
            return False, f"{error_msg}\nError Output:\n{stderr}\nStandard Output:\n{stdout}"

    except FileNotFoundError:
        # This should ideally be caught by is_rclone_available, but as a fallback
        msg = f"Error: The rclone command ('{RCLONE_EXE}') was not found during execution. Please ensure rclone is installed and in your PATH."
        print(f"[RcloneSync] {msg}")
        return False, msg
    except Exception as e:
        msg = f"An unexpected error occurred during rclone execution: {e}"
        print(f"[RcloneSync] {msg}")
        return False, msg

if __name__ == '__main__':
    print("Testing rclone_sync.py...")

    if not is_rclone_available():
        print("WARNING: rclone is not available on this system. Sync tests will be skipped.")
    else:
        print(f"rclone found at: {RCLONE_EXE}")
        # Create dummy source and destination for local test
        os.makedirs("temp_rclone_source", exist_ok=True)
        os.makedirs("temp_rclone_dest", exist_ok=True)

        with open("temp_rclone_source/test_file1.txt", "w") as f:
            f.write("This is a test file for rclone sync.")
        with open("temp_rclone_source/test_file2.txt", "w") as f:
            f.write("Another test file.")

        print("\n--- Test 1: Local source to local destination ---")
        # Note: For actual remote tests, rclone needs to be configured (e.g. with `rclone config`)
        # and the remote names (like 'myremote:') must match that configuration.
        # This example uses local paths which rclone also supports.
        success, message = sync_data_with_rclone("temp_rclone_source/", "temp_rclone_dest/")
        print(f"Sync Result: Success={success}")
        print(message)

        if success:
            print("Verifying files in destination:")
            print(os.listdir("temp_rclone_dest/"))

        # Example of how a remote sync might look (will likely fail if 'myremote:' is not configured)
        # print("\n--- Test 2: Local source to (mock) remote destination (EXPECTS FAILURE if not configured) ---")
        # success_remote, message_remote = sync_data_with_rclone("temp_rclone_source/", "myremote:backup_test/")
        # print(f"Remote Sync Result: Success={success_remote}")
        # print(message_remote)

        # Cleanup dummy directories (optional)
        # import shutil
        # shutil.rmtree("temp_rclone_source")
        # shutil.rmtree("temp_rclone_dest")

    print("\nTo test with a real remote, configure rclone (e.g., 'rclone config')")
    print("Then use a command like: python src/tools/rclone_sync.py")
    print("And modify the __main__ block to use your configured remote name (e.g., 'mycloudstorage:myfolder').")
