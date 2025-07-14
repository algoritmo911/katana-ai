import time
import os  # Added for dummy log file creation in __main__
import json  # For writing status file
from typing import Dict, List, Any

from . import self_healing_config as config
from .self_healing_logger import logger
from .monitor import ServiceMonitor
from .diagnostics import IssueDiagnoser
from .recovery import RecoveryManager


class SelfHealingOrchestrator:
    """
    Coordinates the entire self-healing process: monitoring, diagnosis, and recovery.
    Manages the main operational loop of the self-healing module.
    """

    def __init__(self):
        if not config.MODULE_ENABLED:
            logger.info(
                "Self-Healing Module is disabled in the configuration. Orchestrator will not run."
            )
            self.is_enabled = False
            return

        self.is_enabled = True
        logger.info("Initializing Self-Healing Orchestrator...")
        self.monitor = ServiceMonitor()
        self.diagnoser = IssueDiagnoser()
        self.recovery_manager = RecoveryManager()

        self.loop_interval_seconds = config.MAIN_LOOP_INTERVAL_SECONDS
        self.max_consecutive_recovery_attempts = (
            config.MAX_CONSECUTIVE_RECOVERY_ATTEMPTS
        )

        # State to track ongoing issues and recovery attempts to avoid loops
        # Key: A unique identifier for an issue (e.g., target_id + issue_type + specific details hash)
        # Value: Dict containing 'first_detected', 'last_detected', 'recovery_attempts_count', 'last_recovery_attempt_ts'
        self.active_issues_state: Dict[str, Dict[str, Any]] = {}
        self.recent_recovery_actions: List[Dict[str, Any]] = (
            []
        )  # Store last N recovery actions
        self.max_recent_actions = 5  # Max number of recent recovery actions to store

        self.status_file_path = os.path.join(
            config.PROJECT_BASE_DIR, "self_healing_status.json"
        )

        logger.info("Self-Healing Orchestrator initialized.")

    def _generate_issue_key(self, issue: Dict[str, Any]) -> str:
        """Generates a consistent key for an issue to track its state."""
        # Basic key: target_id and issue_type. More specific details can be added for finer granularity.
        key_parts = [
            str(issue.get("target_id", "unknown_target")),
            str(issue.get("issue_type", "unknown_issue")),
        ]
        # Add some detail to differentiate similar issues on same target, if available
        details = issue.get("details")
        if isinstance(details, str) and len(details) > 0:
            # Take a small part of details to avoid overly long keys
            key_parts.append(details[:50])

        return "_".join(key_parts).replace(" ", "_").lower()

    def run_cycle(self):
        """
        Executes a single cycle of monitoring, diagnosis, and recovery.
        """
        if not self.is_enabled:
            return

        logger.info("Starting new self-healing cycle...")

        # 1. Monitor
        logger.info("Phase 1: Monitoring")
        monitor_data = self.monitor.run_all_checks()
        if not monitor_data:
            logger.info(
                "Monitoring phase yielded no data. Cycle might end early if no issues to process."
            )
            # Even if no new data, existing active issues might need re-evaluation or expiry logic here.

        # 2. Diagnose
        logger.info("Phase 2: Diagnosis")
        # Pass current monitor_data. If empty, diagnoser might not find new issues
        # but could potentially re-evaluate based on a lack of "ok" signals if designed to do so.
        diagnosed_issues = self.diagnoser.run_diagnostics(monitor_data)

        if not diagnosed_issues:
            logger.info("Diagnosis phase found no new issues.")
            # Consider cleanup for issues that are no longer detected (self-resolved)
            self._cleanup_resolved_issues(
                monitor_data
            )  # Pass monitor data to see what's now OK
            logger.info("Self-healing cycle complete. No active issues to address.")
            return

        logger.info(f"Diagnosis phase identified {len(diagnosed_issues)} issues.")

        # 3. Recover
        logger.info("Phase 3: Recovery")
        issues_to_attempt_recovery: List[Dict[str, Any]] = []
        current_time = time.time()

        for issue in diagnosed_issues:
            issue_key = self._generate_issue_key(issue)

            if issue_key not in self.active_issues_state:
                self.active_issues_state[issue_key] = {
                    "first_detected_ts": current_time,
                    "last_detected_ts": current_time,
                    "recovery_attempts_count": 0,
                    "last_recovery_attempt_ts": 0,
                    "original_issue_details": issue,  # Store the first instance of the issue
                }
                logger.info(
                    f"New issue detected and tracked: {issue_key} - {issue.get('issue_type')}"
                )
                issues_to_attempt_recovery.append(issue)
            else:
                # Issue was already active
                self.active_issues_state[issue_key]["last_detected_ts"] = current_time
                attempts_count = self.active_issues_state[issue_key][
                    "recovery_attempts_count"
                ]

                if attempts_count < self.max_consecutive_recovery_attempts:
                    logger.info(
                        f"Previously detected issue '{issue_key}' still active. Will attempt recovery (attempt {attempts_count + 1})."
                    )
                    issues_to_attempt_recovery.append(issue)
                else:
                    logger.warning(
                        f"Issue '{issue_key}' has reached max recovery attempts ({attempts_count}). No further automatic recovery will be attempted for this instance unless state is reset."
                    )
                    # Potentially escalate here: send notification, log critical error, etc.

        if not issues_to_attempt_recovery:
            logger.info(
                "No issues eligible for recovery in this cycle (either new or within attempt limits)."
            )
        else:
            recovery_results = self.recovery_manager.attempt_all_recoveries(
                issues_to_attempt_recovery
            )
            for result in recovery_results:
                # Update active_issues_state based on recovery outcome
                issue_key_for_result = self._generate_issue_key(
                    result
                )  # Assuming result contains enough info to regen key
                if issue_key_for_result in self.active_issues_state:
                    self.active_issues_state[issue_key_for_result][
                        "recovery_attempts_count"
                    ] += 1
                    self.active_issues_state[issue_key_for_result][
                        "last_recovery_attempt_ts"
                    ] = current_time
                    if result.get("status") == "success":
                        logger.info(
                            f"Recovery successful for issue related to '{issue_key_for_result}'. It might be cleared in the next cycle if checks pass."
                        )
                    else:
                        logger.warning(
                            f"Recovery failed or skipped for issue related to '{issue_key_for_result}'. Status: {result.get('status')}"
                        )
                    self._add_recovery_action_to_history(
                        result
                    )  # Add to history regardless of success/failure
                else:
                    logger.warning(
                        f"Recovery result for an untracked or differently keyed issue: {result}"
                    )
                    # Potentially add to history even if untracked, if result has enough info
                    # self._add_recovery_action_to_history(result)

        self._cleanup_resolved_issues(monitor_data)
        self._write_status_file(
            monitor_data
        )  # Pass current monitor_data for target statuses
        logger.info("Self-healing cycle complete.")

    def _add_recovery_action_to_history(self, recovery_result: Dict[str, Any]):
        """Adds a recovery action to the recent history, maintaining max size."""
        if not recovery_result or not isinstance(recovery_result, dict):
            return

        action_summary = {
            "timestamp": recovery_result.get(
                "timestamp", time.time()
            ),  # Ensure timestamp from result or now
            "target_id": recovery_result.get("target_id"),
            "issue_type": recovery_result.get("issue_type"),
            "action": recovery_result.get("action_taken", "Unknown action"),
            "outcome": recovery_result.get("status", "unknown"),
        }
        self.recent_recovery_actions.append(action_summary)
        # Keep only the last N actions
        if len(self.recent_recovery_actions) > self.max_recent_actions:
            self.recent_recovery_actions = self.recent_recovery_actions[
                -self.max_recent_actions :
            ]

    def _write_status_file(self, current_monitor_data: Dict[str, List[Dict[str, Any]]]):
        """Writes the current operational status to a JSON file."""
        logger.debug(f"Writing self-healing status to {self.status_file_path}")

        # Prepare monitored targets status
        monitored_targets_summary = {}
        if current_monitor_data:
            for target_id, data_list in current_monitor_data.items():
                if data_list:  # Should always have at least one entry from monitor
                    # Use the first (often only) data point for summary
                    # A more complex summary might aggregate if multiple data_points exist
                    dp = data_list[0]
                    monitored_targets_summary[target_id] = {
                        "last_check_ts": dp.get(
                            "timestamp"
                        ),  # Assuming monitor adds this
                        "status": dp.get("status", "unknown"),
                        "details": dp.get("error_message")
                        or dp.get("details", ""),  # Prioritize error_message
                    }
                else:
                    monitored_targets_summary[target_id] = {
                        "status": "nodata",
                        "details": "No data from monitor",
                    }

        # Prepare active issues summary
        active_issues_summary_list = []
        for key, issue_data in self.active_issues_state.items():
            original_details = issue_data.get("original_issue_details", {})
            active_issues_summary_list.append(
                {
                    "key": key,
                    "target_id": original_details.get("target_id"),
                    "issue_type": original_details.get("issue_type"),
                    "first_detected_ts": issue_data.get("first_detected_ts"),
                    "last_detected_ts": issue_data.get("last_detected_ts"),
                    "attempts": issue_data.get("recovery_attempts_count"),
                }
            )

        status_payload = {
            "last_updated_ts": time.time(),
            "daemon_status": "RUNNING",  # Could be more dynamic later
            "pid": os.getpid(),  # PID of the orchestrator process itself
            "active_issues_count": len(self.active_issues_state),
            "active_issues_summary": active_issues_summary_list,
            "monitored_targets_status": monitored_targets_summary,
            "recent_recovery_actions": self.recent_recovery_actions,  # Already pruned
        }

        try:
            temp_status_file_path = self.status_file_path + ".tmp"
            with open(temp_status_file_path, "w") as f:
                json.dump(status_payload, f, indent=2)
            os.replace(temp_status_file_path, self.status_file_path)  # Atomic replace
            logger.debug(f"Successfully wrote status to {self.status_file_path}")
        except IOError as e:
            logger.error(
                f"Failed to write self-healing status to {self.status_file_path}: {e}"
            )
        except Exception as e:
            logger.error(f"Unexpected error writing status file: {e}", exc_info=True)

    def _cleanup_resolved_issues(
        self, current_monitor_data: Dict[str, List[Dict[str, Any]]]
    ):
        """
        Identifies issues that are no longer present based on current monitoring data
        and removes them from the active_issues_state.
        This is a simplistic approach; more sophisticated logic might be needed.
        """
        logger.debug("Running cleanup for resolved issues...")
        resolved_issue_keys = []

        # Build a set of "OK" signals from current monitor data
        # An "OK" signal could be a specific status, or simply the presence of data for a target
        # without any associated errors from that target's monitors.
        currently_ok_targets_and_aspects = set()
        for target_id, data_list in current_monitor_data.items():
            target_has_error_reports = False
            for data_point in data_list:
                # Define what constitutes an "error" status from a monitor.
                # This might need to be more nuanced based on plugin outputs.
                if (
                    data_point.get("status") == "error"
                    or data_point.get("status") == "warning"
                ):  # Example criteria
                    target_has_error_reports = True
                    break
            if not target_has_error_reports:
                # If a target reported data and none of it was an error, consider it generally OK for now.
                # This is a simplification. A more robust check would look at specific issue types.
                currently_ok_targets_and_aspects.add(target_id)

        for issue_key, issue_state_data in list(self.active_issues_state.items()):
            original_issue = issue_state_data.get("original_issue_details", {})
            target_id = original_issue.get("target_id")

            # DEBUG LOGGING FOR TEST 5
            if (
                target_id == "service_B" and issue_key == "service_b_disk_full"
            ):  # Matches key2 from test
                # Ensure logger is at a level that will show warnings during tests if not CRITICAL
                # Test setup has logger.setLevel("CRITICAL"), so this won't show unless changed.
                # Forcing a print for test debug purposes:
                print(
                    f"DEBUG_CLEANUP: Key {issue_key}, Target {target_id}. In currently_ok: {target_id in currently_ok_targets_and_aspects}. Is stale: {time.time() - issue_state_data['last_detected_ts'] > (self.loop_interval_seconds * 5)}. Staleness threshold: {self.loop_interval_seconds*5}, time_diff: {time.time() - issue_state_data['last_detected_ts']}"
                )

            # Simplistic check: If the target_id associated with the issue is now reporting "OK"
            # and no specific error matching the issue type is found for that target in current diagnostics (harder to check here without re-diagnosing),
            # assume it might be resolved.
            # A better way: Check if a *new* diagnostic run on current_monitor_data *still* reports this specific issue_key.
            # For now, if its primary target is in the "currently_ok_targets_and_aspects", we consider it potentially resolved.
            if target_id in currently_ok_targets_and_aspects:
                # More refined: Check if the *specific* condition that caused the issue is gone.
                # E.g., if it was an API error, is the API now responding with status OK?
                # This requires more detailed info from monitor_data or re-diagnosis.
                logger.info(
                    f"Issue '{issue_key}' for target '{target_id}' seems resolved as target is now reporting OK. Removing from active issues."
                )
                resolved_issue_keys.append(issue_key)
            else:
                # Issue's target is not in the "OK" list, or no data for it, so it's likely still active or status unknown.
                # Add staleness check: if an issue hasn't been detected for a while, even if not explicitly "OK", remove it.
                staleness_threshold = self.loop_interval_seconds * 5  # e.g., 5 cycles
                if (
                    time.time() - issue_state_data["last_detected_ts"]
                    > staleness_threshold
                ):
                    logger.info(
                        f"Issue '{issue_key}' has not been re-detected recently. Marking as stale and removing from active issues."
                    )
                    resolved_issue_keys.append(issue_key)

        for key_to_remove in resolved_issue_keys:
            if key_to_remove in self.active_issues_state:
                del self.active_issues_state[key_to_remove]

        if resolved_issue_keys:
            logger.info(
                f"Cleaned up {len(resolved_issue_keys)} resolved or stale issues from active state."
            )
        else:
            logger.debug(
                "No issues found to be resolved or stale in this cleanup pass."
            )

    def start(self):
        """
        Starts the main loop of the self-healing orchestrator.
        """
        if not self.is_enabled:
            logger.warning(
                "Orchestrator start called, but module is disabled. Will not run healing loop."
            )
            return

        logger.info(
            f"Self-Healing Orchestrator starting main loop. Cycle interval: {self.loop_interval_seconds}s"
        )
        try:
            while True:
                self.run_cycle()
                logger.info(
                    f"Next self-healing cycle in {self.loop_interval_seconds} seconds."
                )
                time.sleep(self.loop_interval_seconds)
        except KeyboardInterrupt:
            logger.info(
                "Self-Healing Orchestrator received KeyboardInterrupt. Shutting down."
            )
        except Exception as e:
            logger.critical(
                f"Self-Healing Orchestrator encountered a critical error in main loop: {e}",
                exc_info=True,
            )
        finally:
            logger.info("Self-Healing Orchestrator stopped.")


if __name__ == "__main__":
    # This requires all underlying modules (monitor, diagnostics, recovery) and their plugins to be set up
    # as well as the self_healing_config.py.

    # For standalone testing, ensure that:
    # 1. `alg911.catana-ai/self_healing/plugins/basic_plugins.py` is populated with
    #    HttpAvailabilityMonitor, ProcessRunningMonitor, LogFileMonitor (Monitoring)
    #    HttpStatusIssueDiagnoser, ProcessNotRunningDiagnoser, LogPatternDiagnoser (Diagnostic)
    #    ServiceRestartRecovery (Recovery)
    #    ...and any other plugins referenced in `self_healing_config.py`.
    # 2. `alg911.catana-ai/self_healing/self_healing_config.py` defines `MONITORED_TARGETS`
    #    that use these plugins.
    # 3. `alg911.catana-ai/logs/` directory is writable for `self_healing.log`.

    logger.info("Starting SelfHealingOrchestrator direct test...")

    # Create dummy files/services that the plugins might check, if necessary for testing.
    # For example, if HttpAvailabilityMonitor checks 'http://localhost:XXXX', ensure something runs there or mock it.
    # If LogFileMonitor checks a file, create it.

    # Example: Ensure katana_events.log exists for LogFileMonitor as configured
    try:
        events_log_path = (
            config.MONITORED_TARGETS.get("katana_events_log", {})
            .get("config", {})
            .get("log_file_path")
        )
        if events_log_path:
            if not os.path.exists(os.path.dirname(events_log_path)):
                os.makedirs(os.path.dirname(events_log_path), exist_ok=True)
            if not os.path.exists(events_log_path):
                with open(events_log_path, "w") as f:
                    f.write("Initial line in dummy events log for testing.\n")
                logger.info(f"Created dummy log file: {events_log_path}")
    except Exception as e:
        logger.warning(f"Could not create dummy log file for testing: {e}")

    orchestrator = SelfHealingOrchestrator()
    if orchestrator.is_enabled:
        # To run a few cycles for testing:
        # orchestrator.start() # This will run indefinitely

        # Or run a few cycles manually:
        for i in range(2):  # Run 2 cycles for this test
            if not orchestrator.is_enabled:
                break
            logger.info(f"\n--- Orchestrator Test: Manual Cycle {i+1} ---")
            orchestrator.run_cycle()
            if (
                i < 1 and orchestrator.is_enabled
            ):  # Don't sleep after the last test cycle
                logger.info(
                    f"Waiting for {orchestrator.loop_interval_seconds}s before next test cycle..."
                )
                time.sleep(orchestrator.loop_interval_seconds)
        logger.info("Orchestrator manual cycles test finished.")
    else:
        logger.info("Orchestrator is disabled, test concludes.")

    print(
        f"Orchestrator testing complete. Check logs at: {config.LOG_FILE_PATH if hasattr(config, 'LOG_FILE_PATH') else 'self_healing.log'}"
    )
