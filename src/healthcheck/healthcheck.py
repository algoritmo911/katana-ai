import json
import os
import subprocess
import yaml
from datetime import datetime, timezone

from src.utils.standard_logger import get_logger

# Configure logging
logger = get_logger(__name__)

# Define file paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
COMMANDS_FILE = os.path.join(PROJECT_ROOT, "katana.commands.json")
HISTORY_FILE = os.path.join(PROJECT_ROOT, "katana.history.json")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "healthcheck_reports")
HEALTH_REPORT_FILE = os.path.join(REPORTS_DIR, "health_report.json")
DIAGNOSTIC_LOG_FILE = os.path.join(REPORTS_DIR, "diagnostic_log.yaml")


def _validate_json_file(filepath, diagnostic_log):
    """Validates a single JSON file."""
    file_status = {"exists": False, "is_valid_json": False, "is_not_empty": False, "error": None}
    log_event_id = f"validate_json_{os.path.basename(filepath)}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    log_entry = {"event_id": log_event_id, "file": filepath, "timestamp": datetime.now(timezone.utc).isoformat()}

    if not os.path.exists(filepath):
        logger.warning(f"File not found: {filepath}")
        log_entry["status"] = "not_found"
        diagnostic_log.append(log_entry)
        file_status["error"] = "File not found"
        return file_status

    file_status["exists"] = True
    log_entry["exists"] = True

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                logger.warning(f"File is empty: {filepath}")
                log_entry["status"] = "empty_file"
                file_status["error"] = "File is empty"
                # Still append log_entry later, after all checks for this file
            else:
                file_status["is_not_empty"] = True

            json.loads(content) # Attempt to parse
            file_status["is_valid_json"] = True
            # If it was empty but valid (e.g., "{}"), is_valid_json is true, error might still be "File is empty"
            # Overwrite status to "valid" only if no prior error like "empty_file" was set.
            if file_status.get("error") == "File is empty" and file_status["is_valid_json"]:
                # It's an empty file that is also valid JSON. Decide how to classify.
                # For now, let's keep the "empty_file" error and also mark is_valid_json = True.
                log_entry["status"] = "valid_but_empty_json" # Custom status
            elif not file_status.get("error"):
                 log_entry["status"] = "valid"
            logger.info(f"File JSON is valid: {filepath}")

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in {filepath}: {e}")
        log_entry["status"] = "invalid_json"
        log_entry["error_details"] = str(e)
        file_status["error"] = f"Invalid JSON: {e}"
    except IOError as e:
        logger.error(f"Error reading file {filepath}: {e}")
        log_entry["status"] = "read_error"
        log_entry["error_details"] = str(e)
        file_status["error"] = f"IOError: {e}"

    diagnostic_log.append(log_entry)
    return file_status


def check_katana_files(diagnostic_log):
    """Checks existence and validity of katana.commands.json and katana.history.json."""
    logger.info("Starting validation of Katana files.")
    diagnostic_log.append({"event": "Katana files validation started", "timestamp": datetime.now(timezone.utc).isoformat()})
    files_to_check = {"commands_file": COMMANDS_FILE, "history_file": HISTORY_FILE}
    results = {}
    for name, path in files_to_check.items():
        results[name] = _validate_json_file(path, diagnostic_log)
    diagnostic_log.append({"event": "Katana files validation completed", "timestamp": datetime.now(timezone.utc).isoformat(), "summary_results": results})
    logger.info("Katana files validation completed.")
    return results


def check_rclone(diagnostic_log):
    """Checks if rclone is installed and accessible by running 'rclone listremotes'."""
    logger.info("Starting rclone check.")
    diagnostic_log.append({"event": "rclone check started", "timestamp": datetime.now(timezone.utc).isoformat()})

    rclone_status = {"installed": False, "accessible": False, "remotes": None, "error": None}
    log_entry = {"event": "rclone_check_attempt", "timestamp": datetime.now(timezone.utc).isoformat()}

    try:
        # Using shell=True can be a security risk if command is from untrusted input,
        # but 'rclone listremotes' is a fixed command here.
        # Consider specifying full path to rclone if it's not in PATH.
        process = subprocess.run(['rclone', 'listremotes'], capture_output=True, text=True, check=False, timeout=30)

        rclone_status["installed"] = True # If command runs, it's installed.
        log_entry["installed_assumption"] = True

        if process.returncode == 0:
            remotes = process.stdout.strip().splitlines()
            rclone_status["accessible"] = True
            rclone_status["remotes"] = remotes if remotes else [] # Ensure it's a list
            logger.info(f"rclone is accessible. Remotes: {remotes}")
            log_entry["status"] = "success"
            log_entry["remotes"] = remotes
        else:
            error_message = f"rclone command failed with exit code {process.returncode}. Stderr: {process.stderr.strip()}"
            logger.error(error_message)
            rclone_status["error"] = error_message
            log_entry["status"] = "command_failed"
            log_entry["return_code"] = process.returncode
            log_entry["stderr"] = process.stderr.strip()
            if "command not found" in process.stderr.lower() or process.returncode == 127: # Common for command not found
                 rclone_status["installed"] = False # Override previous assumption
                 log_entry["installed_assumption"] = False


    except FileNotFoundError:
        logger.error("rclone command not found. Ensure rclone is installed and in PATH.")
        rclone_status["error"] = "rclone command not found"
        log_entry["status"] = "not_found_error"
        rclone_status["installed"] = False
    except subprocess.TimeoutExpired:
        logger.error("rclone command timed out.")
        rclone_status["error"] = "rclone command timed out"
        log_entry["status"] = "timeout_error"
        # installed might be true, but it's not responsive
    except Exception as e:
        logger.error(f"An unexpected error occurred while checking rclone: {e}")
        rclone_status["error"] = f"Unexpected error: {str(e)}"
        log_entry["status"] = "unexpected_error"
        log_entry["error_details"] = str(e)

    diagnostic_log.append(log_entry)
    diagnostic_log.append({"event": "rclone check completed", "timestamp": datetime.now(timezone.utc).isoformat(), "summary_result": rclone_status})
    logger.info("rclone check completed.")
    return rclone_status


def run_healthcheck():
    """Runs all health check procedures."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    diagnostic_log = []
    health_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "katana_files_status": {},
        "rclone_status": {},
        "report_files_status": {}
    }

    logger.info("Health check process started.")
    diagnostic_log.append({"event": "Health check started", "timestamp": datetime.now(timezone.utc).isoformat()})

    health_report["katana_files_status"] = check_katana_files(diagnostic_log)
    health_report["rclone_status"] = check_rclone(diagnostic_log)

    try:
        with open(HEALTH_REPORT_FILE, 'w', encoding='utf-8') as f:
            json.dump(health_report, f, indent=4)
        diagnostic_log.append({"event": f"Successfully generated {HEALTH_REPORT_FILE}", "status": "success", "timestamp": datetime.now(timezone.utc).isoformat()})
        health_report["report_files_status"][HEALTH_REPORT_FILE] = "Generated"
    except IOError as e:
        logger.error(f"Failed to write health report: {e}")
        diagnostic_log.append({"event": f"Failed to generate {HEALTH_REPORT_FILE}", "error": str(e), "status": "failure", "timestamp": datetime.now(timezone.utc).isoformat()})
        health_report["report_files_status"][HEALTH_REPORT_FILE] = f"Error: {str(e)}"

    diagnostic_log.append({"event": "Health check process completing", "timestamp": datetime.now(timezone.utc).isoformat()})
    try:
        with open(DIAGNOSTIC_LOG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(diagnostic_log, f, allow_unicode=True, sort_keys=False)
        logger.info(f"Successfully generated {DIAGNOSTIC_LOG_FILE}")
    except IOError as e:
        logger.error(f"Failed to write diagnostic log: {e}")

    logger.info("Health check process completed.")

if __name__ == "__main__":
    # Create dummy files for testing if they don't exist
    if not os.path.exists(COMMANDS_FILE):
        with open(COMMANDS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"commands": ["sample command"]}, f) # Add some content
    if not os.path.exists(HISTORY_FILE):
        # Create an empty but valid JSON history file
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

    run_healthcheck()
    print(f"Health check complete. Reports generated in {REPORTS_DIR}/")
    print(f"Please inspect: {HEALTH_REPORT_FILE} and {DIAGNOSTIC_LOG_FILE}")
