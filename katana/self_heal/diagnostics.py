import hashlib
import os
import re
from collections import Counter

def calculate_hash(file_path):
    """Calculates the SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def check_module_integrity(module_path, expected_hash):
    """Checks the integrity of a module by comparing its hash with an expected hash."""
    if not os.path.exists(module_path):
        return False, "Module not found."

    actual_hash = calculate_hash(module_path)
    if actual_hash == expected_hash:
        return True, "Integrity check passed."
    else:
        return False, f"Integrity check failed. Expected {expected_hash}, but got {actual_hash}."

def analyze_logs(log_file):
    """
    Analyzes a log file to find lines containing error-related keywords.

    :param log_file: Path to the log file.
    :return: A tuple containing a list of error lines and a status message.
             Returns (None, message) if the file cannot be read.
    """
    if not os.path.exists(log_file):
        return None, f"Log file not found at '{log_file}'."

    error_patterns = [
        r"error",
        r"exception",
        r"traceback",
        r"critical",
        r"failed",
    ]

    errors_found = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                for pattern in error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        errors_found.append(line.strip())
                        break  # Move to the next line after finding one match
    except Exception as e:
        return None, f"Failed to read or process log file: {e}"

    if not errors_found:
        return [], "No errors found in logs."

    return errors_found, f"Found {len(errors_found)} error-related lines."
