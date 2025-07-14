import os
import time
import subprocess
import requests  # external dependency
from typing import Any, Dict, List

from ..plugin_interface import MonitoringPlugin, DiagnosticPlugin, RecoveryPlugin
from ..self_healing_logger import (
    logger,
)  # Assuming logger is accessible from parent package

# --- Monitoring Plugins ---


class HttpAvailabilityMonitor(MonitoringPlugin):
    def get_name(self) -> str:
        return "HttpAvailabilityMonitor"

    def check_health(self, config: Dict[str, Any]) -> Dict[str, Any]:
        url = config.get("url")
        method = config.get("method", "GET").upper()
        expected_status_code = config.get("expected_status_code", 200)
        timeout_seconds = config.get("timeout_seconds", 10)
        headers = config.get("headers", {})
        payload = config.get("payload")  # For POST, PUT, etc.

        if not url:
            return {
                "status": "error",
                "error_message": "URL not configured for HttpAvailabilityMonitor",
            }

        logger.debug(
            f"{self.get_name()}: Checking {method} {url} (expecting {expected_status_code})"
        )
        result_data: Dict[str, Any] = {
            "url": url,
            "method": method,
            "expected_status_code": expected_status_code,
        }

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=payload,
                timeout=timeout_seconds,
                allow_redirects=True,
            )
            result_data["http_status_code"] = response.status_code
            result_data["response_time_ms"] = response.elapsed.total_seconds() * 1000

            if response.status_code == expected_status_code:
                result_data["status"] = "ok"
                result_data["details"] = (
                    f"Service responded with {response.status_code} as expected."
                )
            else:
                result_data["status"] = "error"
                result_data["error_message"] = (
                    f"Unexpected status code: {response.status_code}. Expected: {expected_status_code}."
                )
                try:
                    result_data["response_content_snippet"] = response.text[
                        :200
                    ]  # First 200 chars
                except Exception:
                    result_data["response_content_snippet"] = (
                        "Could not retrieve response content."
                    )
            logger.debug(
                f"{self.get_name()}: Check for {url} result: {result_data['status']}"
            )
        except requests.exceptions.Timeout:
            result_data["status"] = "error"
            result_data["error_message"] = (
                f"Request timed out after {timeout_seconds} seconds."
            )
            logger.warning(f"{self.get_name()}: Timeout checking {url}.")
        except requests.exceptions.RequestException as e:
            result_data["status"] = "error"
            result_data["error_message"] = f"Request failed: {str(e)}"
            logger.warning(f"{self.get_name()}: RequestException checking {url}: {e}")
        except Exception as e:
            result_data["status"] = "error"
            result_data["error_message"] = f"An unexpected error occurred: {str(e)}"
            logger.error(
                f"{self.get_name()}: Unexpected error checking {url}: {e}",
                exc_info=True,
            )

        return result_data


class ProcessRunningMonitor(MonitoringPlugin):
    def get_name(self) -> str:
        return "ProcessRunningMonitor"

    def check_health(self, config: Dict[str, Any]) -> Dict[str, Any]:
        process_name_pattern = config.get("process_name_pattern")
        pid_file = config.get("pid_file")
        result_data: Dict[str, Any] = {
            "process_name_pattern": process_name_pattern,
            "pid_file": pid_file,
        }

        if not process_name_pattern and not pid_file:
            result_data["status"] = "error"
            result_data["error_message"] = (
                "Either 'process_name_pattern' or 'pid_file' must be configured."
            )
            return result_data

        pids_found = []
        if pid_file:
            logger.debug(f"{self.get_name()}: Checking PID file {pid_file}")
            try:
                if os.path.exists(pid_file):
                    with open(pid_file, "r") as f:
                        pid_str = f.read().strip()
                        if pid_str.isdigit():
                            pid = int(pid_str)
                            # Check if process with this PID exists
                            if os.path.exists(
                                f"/proc/{pid}"
                            ):  # Linux specific, adjust for other OS
                                pids_found.append(pid)
                                result_data["pid_from_file"] = pid
                            else:
                                result_data["status"] = "error"
                                result_data["error_message"] = (
                                    f"PID {pid} from file {pid_file} does not exist."
                                )
                        else:
                            result_data["status"] = "error"
                            result_data["error_message"] = (
                                f"Content of PID file {pid_file} is not a valid PID: {pid_str}"
                            )
                else:
                    result_data["status"] = "error"
                    result_data["error_message"] = f"PID file {pid_file} not found."
            except Exception as e:
                result_data["status"] = "error"
                result_data["error_message"] = f"Error reading PID file {pid_file}: {e}"
                logger.warning(
                    f"{self.get_name()}: Error with PID file {pid_file}: {e}"
                )

        if (
            process_name_pattern and not pids_found
        ):  # Only check by pattern if PID file didn't yield a running process or wasn't used
            logger.debug(
                f"{self.get_name()}: Checking for process pattern '{process_name_pattern}'"
            )
            try:
                # This is a simplistic check, might need more robust psutil or similar for cross-platform
                # Using 'pgrep' for Linux/macOS like systems.
                # Example: pgrep -f "katana_agent.py"
                cmd = ["pgrep", "-f", process_name_pattern]
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate(timeout=5)

                if process.returncode == 0:
                    pids_str = stdout.decode().strip().split("\n")
                    pids_found.extend([int(p) for p in pids_str if p.isdigit()])
                elif process.returncode == 1:  # No process matched
                    pass  # pids_found remains empty
                else:  # Error running pgrep
                    err_msg = stderr.decode().strip()
                    result_data["status"] = "error"
                    result_data["error_message"] = (
                        f"Error checking process with pgrep: {err_msg}"
                    )
                    logger.warning(
                        f"{self.get_name()}: pgrep error for '{process_name_pattern}': {err_msg}"
                    )

            except FileNotFoundError:  # pgrep not found
                result_data["status"] = "error"
                result_data["error_message"] = (
                    "pgrep command not found. Cannot check process by pattern."
                )
                logger.error(f"{self.get_name()}: pgrep not found.")
            except subprocess.TimeoutExpired:
                result_data["status"] = "error"
                result_data["error_message"] = "pgrep command timed out."
                logger.warning(
                    f"{self.get_name()}: pgrep timeout for '{process_name_pattern}'."
                )
            except Exception as e:
                result_data["status"] = "error"
                result_data["error_message"] = (
                    f"Exception checking process pattern: {e}"
                )
                logger.error(
                    f"{self.get_name()}: Exception with pgrep for '{process_name_pattern}': {e}",
                    exc_info=True,
                )

        if pids_found:
            result_data["status"] = "ok"
            result_data["pids"] = pids_found
            result_data["details"] = f"Process found with PIDs: {pids_found}."
        elif "status" not in result_data:  # If no error occurred but also no PIDs found
            result_data["status"] = (
                "error"  # Changed from "warning" to "error" as it's an issue if not found
            )
            result_data["error_message"] = "Process not found."
            result_data["pids"] = []

        logger.debug(
            f"{self.get_name()}: Check for process '{process_name_pattern or pid_file}' result: {result_data.get('status')}"
        )
        return result_data


class LogFileMonitor(MonitoringPlugin):
    # Track last read position to avoid re-reading entire file each time (simple version)
    # More robust would be using something like `loguru` with sinks or file watching libraries.
    # This simple version just reads recent lines or lines with errors.
    _last_positions: Dict[str, int] = {}
    _last_error_timestamps: Dict[str, float] = (
        {}
    )  # To avoid re-flagging same error burst

    def get_name(self) -> str:
        return "LogFileMonitor"

    def check_health(self, config: Dict[str, Any]) -> Dict[str, Any]:
        log_file_path = config.get("log_file_path")
        error_patterns = config.get("error_patterns", [])  # List of regex strings
        # lookback_lines = config.get("lookback_lines", 200) # How many recent lines to check
        # For simplicity, this version will check for patterns from last read or new errors.
        # A full implementation might use inode and position tracking.

        if not log_file_path:
            return {"status": "error", "error_message": "log_file_path not configured."}
        if not os.path.exists(log_file_path):
            return {
                "status": "warning",
                "log_file": log_file_path,
                "details": "Log file does not exist.",
            }

        logger.debug(
            f"{self.get_name()}: Checking log file '{log_file_path}' for patterns: {error_patterns}"
        )
        found_patterns_details: List[Dict[str, Any]] = []

        try:
            current_pos = self._last_positions.get(log_file_path, 0)
            file_size = os.path.getsize(log_file_path)

            if file_size < current_pos:  # Log file rotated or truncated
                current_pos = 0
                logger.info(
                    f"{self.get_name()}: Log file '{log_file_path}' appears to have rotated/truncated. Resetting read position."
                )

            lines_read_count = 0
            if file_size > current_pos:
                with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(current_pos)
                    for line_number, line_content in enumerate(
                        f, start=int(current_pos / 80)
                    ):  # Approx line number
                        lines_read_count += 1
                        for pattern_index, pattern in enumerate(error_patterns):
                            # Basic string matching, for regex use re.search
                            if (
                                pattern in line_content
                            ):  # Use `re.search(pattern, line_content)` for regex
                                found_patterns_details.append(
                                    {
                                        "pattern": pattern,
                                        "line_number": line_number,  # This is an approximation
                                        "line_content": line_content.strip()[
                                            :200
                                        ],  # Snippet
                                    }
                                )
                    self._last_positions[log_file_path] = f.tell()

            if found_patterns_details:
                # Debounce frequent reporting of same burst of errors
                debounce_period_seconds = 60
                last_err_ts = self._last_error_timestamps.get(log_file_path, 0)
                if time.time() - last_err_ts > debounce_period_seconds:
                    self._last_error_timestamps[log_file_path] = time.time()
                    logger.warning(
                        f"{self.get_name()}: Found {len(found_patterns_details)} pattern matches in '{log_file_path}'. Lines checked: {lines_read_count}"
                    )
                    return {
                        "status": "warning",
                        "log_file": log_file_path,
                        "found_patterns_count": len(found_patterns_details),
                        "details_snippet": found_patterns_details[
                            :3
                        ],  # First 3 matches
                    }
                else:
                    logger.debug(
                        f"{self.get_name()}: Patterns found in '{log_file_path}' but within debounce period. Suppressing new warning status."
                    )
                    return {
                        "status": "ok",
                        "log_file": log_file_path,
                        "details": "Patterns found but debounced.",
                    }

            logger.debug(
                f"{self.get_name()}: No new critical patterns found in '{log_file_path}'. Lines checked: {lines_read_count}"
            )
            return {
                "status": "ok",
                "log_file": log_file_path,
                "details": f"No new error patterns found. Lines checked: {lines_read_count}",
            }

        except Exception as e:
            logger.error(
                f"{self.get_name()}: Error reading log file '{log_file_path}': {e}",
                exc_info=True,
            )
            return {
                "status": "error",
                "log_file": log_file_path,
                "error_message": str(e),
            }


# --- Diagnostic Plugins ---


class HttpStatusIssueDiagnoser(DiagnosticPlugin):
    def get_name(self) -> str:
        return "HttpStatusIssueDiagnoser"

    def diagnose(
        self, monitor_data_list: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        issues = []
        critical_status_codes = config.get(
            "critical_status_codes", [500, 502, 503, 504]
        )

        for data_point in monitor_data_list:
            # Ensure this diagnoser only processes data from HttpAvailabilityMonitor
            if data_point.get("monitor_name") != "HttpAvailabilityMonitor":
                continue

            is_issue = False
            severity = "warning"  # Default severity
            issue_type = "HTTP_GENERIC_ISSUE"
            details = data_point.get("error_message", "No specific error message.")

            if data_point.get("status") == "error":
                is_issue = True
                severity = "critical"  # Most direct errors from monitor are critical
                issue_type = "HTTP_MONITOR_ERROR"  # e.g. timeout, connection refused
                details = data_point.get(
                    "error_message", "HTTP monitor reported an error."
                )

            http_status_code = data_point.get("http_status_code")
            if http_status_code is not None:
                expected_code = data_point.get("expected_status_code")
                if (
                    http_status_code != expected_code
                ):  # Already an issue if codes don't match
                    is_issue = True
                    details = (
                        f"Expected status {expected_code} but got {http_status_code}. "
                        + data_point.get("error_message", "")
                    )
                    issue_type = "HTTP_UNEXPECTED_STATUS_CODE"
                    if http_status_code in critical_status_codes:
                        severity = "critical"
                    elif 400 <= http_status_code < 500:  # Client errors
                        severity = "warning"
                # If it was an expected code, but still in critical list (e.g. expecting 503 for a test)
                elif (
                    http_status_code in critical_status_codes
                    and http_status_code == expected_code
                ):
                    is_issue = (
                        True  # Still log it as an issue if it's inherently critical
                    )
                    severity = "critical"
                    issue_type = "HTTP_EXPECTED_CRITICAL_STATUS"
                    details = f"Received expected critical status {http_status_code}."

            if is_issue:
                issues.append(
                    {
                        "issue_type": issue_type,
                        "severity": severity,
                        "details": details.strip(),
                        "target_id": data_point.get("target_id"),
                        "monitor_name": data_point.get("monitor_name"),
                        "url_checked": data_point.get("url"),
                        "actual_status_code": http_status_code,
                        "source_data_snippet": {
                            k: v
                            for k, v in data_point.items()
                            if k not in ["target_id", "monitor_name"]
                        },
                    }
                )
        if issues:
            logger.debug(f"{self.get_name()} diagnosed {len(issues)} HTTP issues.")
        return issues


class ProcessNotRunningDiagnoser(DiagnosticPlugin):
    def get_name(self) -> str:
        return "ProcessNotRunningDiagnoser"

    def diagnose(
        self, monitor_data_list: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        issues = []
        for data_point in monitor_data_list:
            if data_point.get("monitor_name") != "ProcessRunningMonitor":
                continue

            if data_point.get(
                "status"
            ) == "error" and "Process not found" in data_point.get("error_message", ""):
                issues.append(
                    {
                        "issue_type": "PROCESS_NOT_RUNNING",
                        "severity": "critical",
                        "details": f"Process matching pattern '{data_point.get('process_name_pattern')}' or PID file '{data_point.get('pid_file')}' was not found or monitor error: {data_point.get('error_message')}",
                        "target_id": data_point.get("target_id"),
                        "monitor_name": data_point.get("monitor_name"),
                        "source_data_snippet": {
                            k: v
                            for k, v in data_point.items()
                            if k not in ["target_id", "monitor_name"]
                        },
                    }
                )
            elif data_point.get("status") == "ok" and not data_point.get(
                "pids"
            ):  # Should not happen if status is ok
                issues.append(
                    {
                        "issue_type": "PROCESS_NOT_RUNNING",  # Or inconsistent_monitor_data
                        "severity": "warning",  # Less critical as monitor said OK
                        "details": f"Process monitor reported OK but no PIDs for '{data_point.get('process_name_pattern')}'",
                        "target_id": data_point.get("target_id"),
                        "monitor_name": data_point.get("monitor_name"),
                    }
                )

        if issues:
            logger.debug(f"{self.get_name()} diagnosed {len(issues)} process issues.")
        return issues


class LogPatternDiagnoser(DiagnosticPlugin):
    def get_name(self) -> str:
        return "LogPatternDiagnoser"

    def diagnose(
        self, monitor_data_list: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        issues = []
        # Config for this diagnoser might include severity mapping for patterns, etc.
        critical_pattern_threshold = config.get("critical_pattern_threshold", 1)

        for data_point in monitor_data_list:
            if data_point.get("monitor_name") != "LogFileMonitor":
                continue

            if (
                data_point.get("status") == "warning"
            ):  # LogFileMonitor sets to 'warning' if patterns found
                num_found = data_point.get("found_patterns_count", 0)
                if num_found >= critical_pattern_threshold:
                    issues.append(
                        {
                            "issue_type": "CRITICAL_LOG_PATTERN_DETECTED",
                            "severity": "warning",  # Could be made 'critical' based on pattern types or count
                            "details": f"Found {num_found} critical pattern(s) in log file '{data_point.get('log_file')}'. Snippet: {data_point.get('details_snippet')}",
                            "target_id": data_point.get("target_id"),
                            "monitor_name": data_point.get("monitor_name"),
                            "log_file": data_point.get("log_file"),
                            "patterns_found_details": data_point.get(
                                "details_snippet"
                            ),  # Or full list if needed
                        }
                    )
        if issues:
            logger.debug(
                f"{self.get_name()} diagnosed {len(issues)} log pattern issues."
            )
        return issues


# --- Recovery Plugins ---


class ServiceRestartRecovery(RecoveryPlugin):
    def get_name(self) -> str:
        return "ServiceRestartRecovery"

    def can_recover(self, issue: Dict[str, Any]) -> bool:
        # This plugin can attempt to restart services for critical HTTP errors or process not running
        recoverable_issue_types = [
            "HTTP_MONITOR_ERROR",  # e.g. connection refused, timeout
            "HTTP_UNEXPECTED_STATUS_CODE",  # Especially for 5xx server errors
            "HTTP_EXPECTED_CRITICAL_STATUS",  # If we are monitoring for a bad state that needs restart
            "PROCESS_NOT_RUNNING",
        ]
        if issue.get("issue_type") in recoverable_issue_types:
            # For HTTP issues, only attempt if severity is critical (usually server-side)
            if (
                "HTTP" in issue.get("issue_type", "")
                and issue.get("severity") != "critical"
            ):
                return False
            return True
        return False

    def attempt_recovery(
        self, issue: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Config for this plugin instance might specify the actual service name for systemd/init.d
        # or a script path.
        service_name_from_config = config.get("service_name")
        # Fallback: try to derive service name from issue's target_id if not explicitly set
        service_name_to_operate = service_name_from_config or issue.get("target_id")

        if not service_name_to_operate:
            return {
                "status": "failed",
                "action_taken": "restart_attempt",
                "error_message": "Service name for restart not configured or derivable from issue target_id.",
            }

        # Default command template - very basic, for systemd.
        # Real config should allow specifying full command or script.
        # IMPORTANT: Commands that require sudo need passwordless sudo setup for the user running Katana,
        # or this plugin needs to run with higher privileges (which is a security risk).
        # Using "echo" for safe simulation by default in tests.
        # Actual command might be: "sudo systemctl restart {service_name}"
        # Or a custom script: "/opt/katana/scripts/restart_{service_name}.sh"
        restart_command_template = config.get(
            "restart_command_template",
            "echo Simulating: sudo systemctl restart {service_name}",
        )

        # Allow a direct command override if provided (more flexible)
        direct_command = config.get("direct_restart_command")
        if direct_command:
            command_to_run = direct_command  # Use this directly
        else:
            command_to_run = restart_command_template.format(
                service_name=service_name_to_operate
            )

        logger.info(
            f"{self.get_name()}: Attempting to restart service '{service_name_to_operate}' with command: {command_to_run}"
        )

        try:
            # Using shell=True is a security risk if command_to_run is constructed from untrusted input.
            # Here, it's from config, assumed to be trusted. For better security, avoid shell=True.
            # Pass command as a list of args if shell=False: e.g. ['sudo', 'systemctl', 'restart', service_name_to_operate]
            # This requires command_to_run to be parsed or config to provide list format.
            is_simulation = command_to_run.startswith("echo Simulating:")

            # For non-simulation, consider security implications of subprocess.run(..., shell=True)
            # If not simulating, it's better to split command_to_run into a list if possible
            # and use shell=False. For example:
            # if not is_simulation: cmd_list = shlex.split(command_to_run) else: cmd_list = command_to_run
            # process = subprocess.run(cmd_list, shell=is_simulation, capture_output=True, text=True, timeout=30)

            process = subprocess.run(
                command_to_run, shell=True, capture_output=True, text=True, timeout=30
            )

            if process.returncode == 0:
                logger.info(
                    f"{self.get_name()}: Service '{service_name_to_operate}' restart command executed successfully. Output: {process.stdout.strip()}"
                )
                # It's hard to verify if restart *actually* fixed the issue here.
                # The next monitoring cycle should confirm.
                return {
                    "status": "success",
                    "action_taken": f"Executed restart command for {service_name_to_operate}",
                    "details": f"Command: '{command_to_run}'. Output: {process.stdout.strip()[:200]}",
                }
            else:
                logger.error(
                    f"{self.get_name()}: Service '{service_name_to_operate}' restart command failed. RC: {process.returncode}, Error: {process.stderr.strip()}"
                )
                return {
                    "status": "failed",
                    "action_taken": f"Attempted restart of {service_name_to_operate}",
                    "error_message": f"Command failed with RC {process.returncode}: {process.stderr.strip()[:200]}",
                    "details": f"Command: '{command_to_run}'",
                }

        except subprocess.TimeoutExpired:
            logger.error(
                f"{self.get_name()}: Timeout restarting service {service_name_to_operate} with command: {command_to_run}"
            )
            return {
                "status": "failed",
                "action_taken": f"Restart {service_name_to_operate}",
                "error_message": "Restart command timed out.",
            }
        except FileNotFoundError:  # If the command itself (e.g. systemctl) is not found
            logger.error(
                f"{self.get_name()}: Restart command or script not found: {command_to_run.split()[0]}"
            )
            return {
                "status": "failed",
                "action_taken": f"Restart {service_name_to_operate}",
                "error_message": f"Command not found: {command_to_run.split()[0]}",
            }
        except Exception as e:
            logger.error(
                f"{self.get_name()}: Error restarting service {service_name_to_operate} with command '{command_to_run}': {e}",
                exc_info=True,
            )
            return {
                "status": "failed",
                "action_taken": f"Restart {service_name_to_operate}",
                "error_message": str(e),
            }


# Example of a placeholder for a more complex recovery plugin
class ConfigurationRollbackRecovery(RecoveryPlugin):
    def get_name(self) -> str:
        return "ConfigurationRollbackRecovery"

    def can_recover(self, issue: Dict[str, Any]) -> bool:
        # Define which issues might be solved by a config rollback
        return (
            issue.get("issue_type") == "INVALID_CONFIG_DETECTED"
        )  # Assuming such an issue type exists

    def attempt_recovery(
        self, issue: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        logger.info(
            f"{self.get_name()}: Placeholder - Simulating configuration rollback for {issue.get('target_id')}"
        )
        # Actual logic would involve:
        # 1. Identifying current config version.
        # 2. Finding previous known-good version (from backup, git, etc.).
        # 3. Applying the rollback.
        # 4. Verifying the rollback.
        # This is highly dependent on how configurations are managed in Katana.
        return {
            "status": "skipped",
            "action_taken": "Configuration rollback (simulated)",
            "details": "This is a placeholder plugin.",
        }


if __name__ == "__main__":
    # Basic tests for plugins (can be expanded)
    logger.info("Running basic plugin direct tests...")

    # Test HttpAvailabilityMonitor
    http_monitor = HttpAvailabilityMonitor()
    # google_health = http_monitor.check_health({"url": "https://www.google.com", "expected_status_code": 200})
    # logger.info(f"Google Health Check: {google_health}")
    non_existent_health = http_monitor.check_health(
        {"url": "http://thissitedefinitelydoesnotexist12345.com"}
    )
    logger.info(f"Non-existent Site Check: {non_existent_health}")
    # Example of a site that might return 403 or other non-200
    # github_api_unauth = http_monitor.check_health({"url": "https://api.github.com/user", "expected_status_code": 401}) # Expect 401 if unauth
    # logger.info(f"GitHub API Unauthenticated Check (expect 401): {github_api_unauth}")

    # Test ProcessRunningMonitor
    process_monitor = ProcessRunningMonitor()
    # Try to find 'python' or 'init' process (likely to exist on Linux)
    # Note: 'python' might find many, 'init' should find PID 1 on Linux
    # This test is OS-dependent. For 'pgrep' to work.
    if os.name == "posix":  # Linux, macOS
        # python_process_check = process_monitor.check_health({"process_name_pattern": "python"})
        # logger.info(f"Python Process Check: {python_process_check}")
        # A process that is unlikely to exist
        # non_existent_process_check = process_monitor.check_health({"process_name_pattern": "absolutely_not_a_running_process_xyz"})
        # logger.info(f"Non-existent Process Check: {non_existent_process_check}")
        pass  # Commented out to avoid noise if pgrep not installed or user is not running python
    else:
        logger.info(
            "Skipping ProcessRunningMonitor tests as OS is not POSIX or pgrep might not be available."
        )

    # Test LogFileMonitor
    log_monitor = LogFileMonitor()
    dummy_log_path = "dummy_test_plugin.log"
    with open(dummy_log_path, "w") as f:
        f.write("INFO: System started normally.\n")
        f.write("DEBUG: Detailed debug message.\n")
        f.write("ERROR: A test error occurred!\n")
        f.write("CRITICAL: This is a test CRITICAL message.\n")

    log_check_no_pattern = log_monitor.check_health(
        {"log_file_path": dummy_log_path, "error_patterns": ["NonExistentPattern"]}
    )
    logger.info(f"Log Check (no matching pattern): {log_check_no_pattern}")
    log_check_with_pattern = log_monitor.check_health(
        {"log_file_path": dummy_log_path, "error_patterns": ["ERROR", "CRITICAL"]}
    )
    logger.info(f"Log Check (with matching patterns): {log_check_with_pattern}")
    # Second check to see if debouncing works (if patterns were found)
    if log_check_with_pattern.get("status") == "warning":
        log_check_debounced = log_monitor.check_health(
            {"log_file_path": dummy_log_path, "error_patterns": ["ERROR", "CRITICAL"]}
        )
        logger.info(f"Log Check (debounced?): {log_check_debounced}")

    if os.path.exists(dummy_log_path):
        os.remove(dummy_log_path)

    # Test HttpStatusIssueDiagnoser
    http_diagnoser = HttpStatusIssueDiagnoser()
    http_monitor_outputs = [
        # Case 1: Connection error from monitor
        {
            "target_id": "service1_api",
            "monitor_name": "HttpAvailabilityMonitor",
            "status": "error",
            "error_message": "Connection refused",
            "url": "http://localhost:1234",
        },
        # Case 2: Unexpected 503 status code
        {
            "target_id": "service2_payment",
            "monitor_name": "HttpAvailabilityMonitor",
            "status": "error",
            "http_status_code": 503,
            "expected_status_code": 200,
            "url": "http://service2/pay",
        },
        # Case 3: Expected 200, got 200 (OK)
        {
            "target_id": "service3_user",
            "monitor_name": "HttpAvailabilityMonitor",
            "status": "ok",
            "http_status_code": 200,
            "expected_status_code": 200,
            "url": "http://service3/user",
        },
        # Case 4: Expected 200, got 404 (Warning)
        {
            "target_id": "service4_docs",
            "monitor_name": "HttpAvailabilityMonitor",
            "status": "error",
            "http_status_code": 404,
            "expected_status_code": 200,
            "url": "http://service4/docs/nonexistent",
        },
    ]
    http_issues = http_diagnoser.diagnose(
        http_monitor_outputs, {"critical_status_codes": [500, 503]}
    )
    logger.info(f"HTTP Diagnoser Issues ({len(http_issues)} found):")
    for issue in http_issues:
        logger.info(f"  - {issue}")

    # Test ServiceRestartRecovery
    restart_recovery = ServiceRestartRecovery()
    test_issue_http_error = {
        "issue_type": "HTTP_MONITOR_ERROR",
        "severity": "critical",
        "target_id": "test_api_service",
    }
    test_issue_process_down = {
        "issue_type": "PROCESS_NOT_RUNNING",
        "severity": "critical",
        "target_id": "test_worker_process",
    }

    can_recover_http = restart_recovery.can_recover(test_issue_http_error)
    logger.info(
        f"Can ServiceRestartRecovery handle HTTP_MONITOR_ERROR? {can_recover_http}"
    )
    if can_recover_http:
        # Config for the plugin instance (service_name might come from MONITORED_TARGETS config in real scenario)
        recovery_config_api = {
            "service_name": "nginx",
            "restart_command_template": "echo Simulating: sudo systemctl restart {service_name}",
        }  # Use a common service for simulation
        recovery_result_api = restart_recovery.attempt_recovery(
            test_issue_http_error, recovery_config_api
        )
        logger.info(f"Recovery attempt for HTTP error: {recovery_result_api}")

    can_recover_process = restart_recovery.can_recover(test_issue_process_down)
    logger.info(
        f"Can ServiceRestartRecovery handle PROCESS_NOT_RUNNING? {can_recover_process}"
    )
    if can_recover_process:
        recovery_config_process = {
            "service_name": "my_custom_worker",
            "direct_restart_command": "echo Simulating: /opt/scripts/restart_my_worker.sh",
        }
        recovery_result_process = restart_recovery.attempt_recovery(
            test_issue_process_down, recovery_config_process
        )
        logger.info(f"Recovery attempt for process down: {recovery_result_process}")

    logger.info("Basic plugin tests complete.")
