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
    """Analyzes a log file to find errors and anomalies."""
    if not os.path.exists(log_file):
        return None, "Log file not found."

    error_patterns = [
        r"error",
        r"exception",
        r"traceback",
    ]

    errors = []
    with open(log_file, "r") as f:
        for line in f:
            for pattern in error_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    errors.append(line)
                    break

    if not errors:
        return [], "No errors found in logs."

    # Anomaly detection (simple example: count frequent errors)
    error_counts = Counter(errors)
    anomalies = [error for error, count in error_counts.items() if count > 5] # Example threshold

    return anomalies, f"Found {len(anomalies)} anomalies."
