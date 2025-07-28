# Katana Health Check Utility

This document describes the health check utility for the Katana application.

## Overview

The health check utility (`src/healthcheck/healthcheck.py`) is a Python script designed to perform a series of checks on the Katana system to ensure its core components are functioning correctly. It generates a JSON health report and a YAML diagnostic log.

## How to Run

To run the health check:

1.  Ensure you are in the root directory of the `katana-ai` repository.
2.  Make sure all dependencies, including `PyYAML`, are installed. You can install them using:
    ```bash
    pip install -r requirements.txt
    ```
3.  Execute the script directly:
    ```bash
    python src/healthcheck/healthcheck.py
    ```
4.  Upon completion, the script will print the location of the generated reports, typically in the `healthcheck_reports/` directory at the project root.

## Checks Performed

The health check utility currently performs the following checks:

1.  **Katana File Validation:**
    *   **`katana.commands.json`**:
        *   Checks for the existence of this file at the project root.
        *   Validates that the file content is valid JSON.
        *   Checks if the file is not empty.
    *   **`katana.history.json`**:
        *   Checks for the existence of this file at the project root.
        *   Validates that the file content is valid JSON.
        *   Checks if the file is not empty.
    *   *Note: If these files do not exist when running the script via `python src/healthcheck/healthcheck.py` directly, the script will create dummy versions for testing purposes.*

2.  **Rclone Availability:**
    *   Checks if the `rclone` command-line tool is installed and accessible in the system's PATH.
    *   Attempts to run `rclone listremotes` to verify its functionality.
    *   Logs the list of detected rclone remotes if successful, or logs errors if `rclone` is not found or the command fails.

## Output Files

The health check utility generates two files in the `healthcheck_reports/` directory (created at the project root):

1.  **`health_report.json`**:
    *   A JSON file summarizing the results of all checks.
    *   Includes a timestamp for the check.
    *   Provides status for Katana file validation (`katana_files_status`) and rclone availability (`rclone_status`).

2.  **`diagnostic_log.yaml`**:
    *   A YAML file containing a detailed, timestamped log of all actions, checks, and their outcomes performed during the health check process.
    *   Useful for debugging and understanding the sequence of operations.

## Future Enhancements

(Placeholder for any future checks or improvements)
