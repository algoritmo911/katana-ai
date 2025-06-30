import json
import subprocess
import os
import datetime
import yaml

# Define file paths (consider making these configurable if needed)
COMMANDS_JSON_PATH = "katana.commands.json"
HISTORY_JSON_PATH = "katana.history.json"
HEALTH_REPORT_PATH = "health_report.json"
DIAGNOSTIC_LOG_PATH = "diagnostic_log.yaml"

def run_healthcheck():
    """
    Runs health checks for Katana's core subsystems.
    Generates a JSON report and logs results to a YAML file.
    """
    health_status = {}
    errors = []

    # 1. Check katana.commands.json
    try:
        if os.path.exists(COMMANDS_JSON_PATH) and os.access(COMMANDS_JSON_PATH, os.R_OK):
            health_status["commands_json"] = "OK"
        else:
            health_status["commands_json"] = "Error: File not found or not readable"
            errors.append(f"{COMMANDS_JSON_PATH} not found or not readable.")
    except Exception as e:
        health_status["commands_json"] = f"Error: {str(e)}"
        errors.append(f"Error checking {COMMANDS_JSON_PATH}: {str(e)}")

    # 2. Check katana.history.json for valid JSON
    try:
        if os.path.exists(HISTORY_JSON_PATH):
            with open(HISTORY_JSON_PATH, 'r') as f:
                json.load(f)
            health_status["history_json"] = "OK"
        else:
            health_status["history_json"] = "Error: File not found"
            errors.append(f"{HISTORY_JSON_PATH} not found.")
    except json.JSONDecodeError:
        health_status["history_json"] = "Error: Invalid JSON"
        errors.append(f"{HISTORY_JSON_PATH} contains invalid JSON.")
    except Exception as e:
        health_status["history_json"] = f"Error: {str(e)}"
        errors.append(f"Error checking {HISTORY_JSON_PATH}: {str(e)}")

    # 3. Check rclone connection
    try:
        result = subprocess.run(['rclone', 'listremotes'], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout:
            health_status["rclone"] = "OK"
        elif result.returncode == 0 and not result.stdout:
            health_status["rclone"] = "Warning: No remotes configured"
        else:
            health_status["rclone"] = f"Error: rclone command failed (exit code {result.returncode})"
            errors.append(f"rclone listremotes failed: {result.stderr.strip()}")
    except FileNotFoundError:
        health_status["rclone"] = "Error: rclone command not found"
        errors.append("rclone command not found. Make sure rclone is installed and in PATH.")
    except Exception as e:
        health_status["rclone"] = f"Error: {str(e)}"
        errors.append(f"Error checking rclone: {str(e)}")

    # Generate JSON report
    try:
        with open(HEALTH_REPORT_PATH, 'w') as f:
            json.dump(health_status, f, indent=4)
    except Exception as e:
        print(f"Error writing health report: {str(e)}") # Log to console if report writing fails

    # Log to diagnostic_log.yaml
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "overall_status": "OK" if not errors else "ERROR",
        "checks": health_status,
        "errors": errors if errors else None
    }

    try:
        log_data = []
        if os.path.exists(DIAGNOSTIC_LOG_PATH):
            with open(DIAGNOSTIC_LOG_PATH, 'r') as f:
                try:
                    log_data = yaml.safe_load(f)
                    if not isinstance(log_data, list): # Ensure it's a list
                        log_data = []
                except yaml.YAMLError:
                    log_data = [] # Start fresh if log is corrupted

        log_data.append(log_entry)

        with open(DIAGNOSTIC_LOG_PATH, 'w') as f:
            yaml.dump(log_data, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        print(f"Error writing diagnostic log: {str(e)}") # Log to console if logging fails

    return health_status, errors

if __name__ == '__main__':
    # This allows testing the module directly
    print("Running healthcheck...")
    status, all_errors = run_healthcheck()
    print("\nHealth Check Status:")
    for check, result in status.items():
        print(f"- {check}: {result}")

    if all_errors:
        print("\nErrors Encountered:")
        for error in all_errors:
            print(f"- {error}")
    else:
        print("\nNo errors encountered. System healthy.")

    print(f"\nReport generated: {HEALTH_REPORT_PATH}")
    print(f"Log updated: {DIAGNOSTIC_LOG_PATH}")
