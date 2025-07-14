import importlib
from typing import Any, Dict, List, Type

from . import self_healing_config as config
from .self_healing_logger import logger
from .plugin_interface import RecoveryPlugin


class RecoveryManager:
    """
    Manages and executes recovery plugins to attempt to fix diagnosed issues.
    """

    def __init__(self):
        self.recovery_plugins: Dict[str, RecoveryPlugin] = {}
        self._load_plugins_from_config()

    def _load_plugin_class(
        self, module_name: str, class_name: str
    ) -> Type[RecoveryPlugin] | None:
        """Dynamically loads a recovery plugin class from a given module."""
        try:
            module = importlib.import_module(module_name)
            plugin_class = getattr(module, class_name)
            if not issubclass(plugin_class, RecoveryPlugin):
                logger.error(
                    f"Plugin class {class_name} from {module_name} does not inherit from RecoveryPlugin."
                )
                return None
            return plugin_class
        except ImportError:
            logger.error(
                f"Failed to import module {module_name} for recovery plugin {class_name}."
            )
            return None
        except AttributeError:
            logger.error(
                f"Class {class_name} not found in module {module_name} for recovery."
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error loading recovery plugin {module_name}.{class_name}: {e}"
            )
            return None

    def _load_plugins_from_config(self):
        """
        Loads recovery plugins based on the MONITORED_TARGETS configuration.
        Assumes recovery plugins are also located in '.plugins.basic_plugins'.
        """
        logger.info("Loading recovery plugins...")
        plugin_module_name_base = (
            ".plugins.basic_plugins"  # Relative to current package 'self_healing'
        )

        unique_plugin_types_to_load: Dict[str, Dict[str, Any]] = {}

        for target_id, target_config in config.MONITORED_TARGETS.items():
            if not target_config.get("enabled", False):
                continue

            recovery_plugin_configs = target_config.get("recovery_plugins", [])
            for plugin_entry in recovery_plugin_configs:
                plugin_class_name = plugin_entry.get("plugin")
                if not plugin_class_name:
                    logger.warning(
                        f"No 'plugin' name specified in recovery_plugins for target '{target_id}'. Skipping entry: {plugin_entry}"
                    )
                    continue

                if plugin_class_name not in unique_plugin_types_to_load:
                    unique_plugin_types_to_load[plugin_class_name] = {
                        "module_name": plugin_module_name_base,  # Assuming all basic recovery plugins are here
                        "class_name": plugin_class_name,
                    }

        for plugin_name, plugin_info in unique_plugin_types_to_load.items():
            module_full_name = f"{__package__}{plugin_info['module_name']}"
            plugin_class = self._load_plugin_class(
                module_full_name, plugin_info["class_name"]
            )
            if plugin_class:
                try:
                    self.recovery_plugins[plugin_name] = plugin_class()
                    logger.info(
                        f"Successfully loaded and instantiated recovery plugin: {plugin_name}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to instantiate recovery plugin {plugin_name}: {e}"
                    )

        logger.info(
            f"Loaded {len(self.recovery_plugins)} unique recovery plugin types."
        )

    def attempt_all_recoveries(
        self, diagnosed_issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Attempts to recover from a list of diagnosed issues.
        It iterates through issues and configured recovery plugins for the target.

        Args:
            diagnosed_issues: A list of issue dictionaries from the IssueDiagnoser.

        Returns:
            A list of recovery attempt result dictionaries.
        """
        all_recovery_results: List[Dict[str, Any]] = []
        logger.info(
            f"Starting recovery attempts for {len(diagnosed_issues)} diagnosed issues..."
        )

        for issue in diagnosed_issues:
            target_id = issue.get("target_id")
            if not target_id:
                logger.warning(
                    f"Issue missing 'target_id', cannot determine recovery path: {issue}"
                )
                all_recovery_results.append(
                    {
                        "status": "skipped",
                        "issue": issue,
                        "reason": "Missing target_id in issue.",
                        "timestamp": logger.handlers[0].formatter.formatTime(
                            logger.makeRecord("", 0, "", "", 0, "", (), None, None)
                        ),
                    }
                )
                continue

            target_config = config.MONITORED_TARGETS.get(target_id)
            if not target_config or not target_config.get("enabled", False):
                logger.debug(
                    f"Target '{target_id}' for issue '{issue.get('issue_type')}' not configured for recovery or is disabled."
                )
                # No explicit result added here, as no recovery was attempted due to config
                continue

            recovery_plugin_configs_for_target = target_config.get(
                "recovery_plugins", []
            )
            if not recovery_plugin_configs_for_target:
                logger.debug(
                    f"No recovery plugins configured for target '{target_id}'. Cannot attempt recovery for issue: {issue.get('issue_type')}"
                )
                continue

            recovered_by_plugin = False
            for plugin_config_entry in recovery_plugin_configs_for_target:
                plugin_name = plugin_config_entry.get("plugin")
                if not plugin_name:
                    logger.warning(
                        f"Recovery plugin entry for '{target_id}' is missing 'plugin' name. Skipping."
                    )
                    continue

                recovery_plugin_instance = self.recovery_plugins.get(plugin_name)
                if not recovery_plugin_instance:
                    logger.error(
                        f"Recovery plugin '{plugin_name}' for target '{target_id}' not found or loaded. Skipping recovery with this plugin."
                    )
                    continue

                if recovery_plugin_instance.can_recover(issue):
                    logger.info(
                        f"Plugin '{recovery_plugin_instance.get_name()}' can attempt recovery for issue: {issue.get('issue_type')} on target '{target_id}'."
                    )
                    plugin_specific_config = plugin_config_entry.get("config", {})

                    try:
                        result = recovery_plugin_instance.attempt_recovery(
                            issue, plugin_specific_config
                        )
                        result["issue_type"] = issue.get("issue_type")
                        result["target_id"] = target_id
                        result["recovered_by"] = recovery_plugin_instance.get_name()
                        result["timestamp"] = logger.handlers[0].formatter.formatTime(
                            logger.makeRecord("", 0, "", "", 0, "", (), None, None)
                        )
                        all_recovery_results.append(result)
                        logger.info(
                            f"Recovery attempt by '{recovery_plugin_instance.get_name()}' for '{target_id} - {issue.get('issue_type')}': {result.get('status')}"
                        )

                        if result.get("status") == "success":
                            recovered_by_plugin = True
                            break  # Stop trying other recovery plugins for this issue if one succeeded
                    except Exception as e:
                        logger.error(
                            f"Error during recovery attempt for '{target_id} - {issue.get('issue_type')}' with plugin '{recovery_plugin_instance.get_name()}': {e}",
                            exc_info=True,
                        )
                        all_recovery_results.append(
                            {
                                "status": "error",
                                "issue_type": issue.get("issue_type"),
                                "target_id": target_id,
                                "recovered_by": recovery_plugin_instance.get_name(),
                                "error_message": f"Exception in plugin: {str(e)}",
                                "timestamp": logger.handlers[0].formatter.formatTime(
                                    logger.makeRecord(
                                        "", 0, "", "", 0, "", (), None, None
                                    )
                                ),
                            }
                        )
                else:
                    logger.debug(
                        f"Plugin '{recovery_plugin_instance.get_name()}' cannot recover issue: {issue.get('issue_type')} on target '{target_id}'."
                    )

            if not recovered_by_plugin:
                logger.info(
                    f"No suitable recovery plugin succeeded or was found for issue: {issue.get('issue_type')} on target '{target_id}'."
                )
                # Optionally add a result indicating no recovery was performed if none of the plugins could handle it or if all failed.
                # This might be redundant if individual plugin failures are already logged.

        logger.info(
            f"Finished recovery attempts. Processed {len(diagnosed_issues)} issues, results: {len(all_recovery_results)}."
        )
        return all_recovery_results


if __name__ == "__main__":
    logger.info("Starting RecoveryManager direct test...")

    # This test requires:
    # 1. self_healing_config.py to be set up with recovery plugin configurations.
    # 2. plugin_interface.py to define RecoveryPlugin.
    # 3. plugins/basic_plugins.py to contain actual recovery plugin classes
    #    referenced in self_healing_config.py (e.g., ServiceRestartRecovery).

    # Mockup of basic_plugins.py for standalone testing (Recovery parts):
    """
    from ..plugin_interface import RecoveryPlugin
    from ..self_healing_logger import logger # Assuming logger is accessible
    import subprocess
    import time

    class ServiceRestartRecovery(RecoveryPlugin):
        def get_name(self) -> str: return "ServiceRestartRecovery"

        def can_recover(self, issue: Dict[str, Any]) -> bool:
            # This plugin can attempt to restart services for critical HTTP errors or process not running
            return issue.get("issue_type") in ["HTTP_SERVICE_ERROR", "HTTP_CRITICAL_STATUS_CODE", "PROCESS_NOT_RUNNING"]

        def attempt_recovery(self, issue: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
            service_name = config.get("service_name", issue.get("target_id")) # Fallback to target_id if not specified
            if not service_name:
                return {"status": "failed", "action_taken": "restart_attempt", "error_message": "Service name not configured or derivable."}

            restart_command_template = config.get("restart_command_template", "echo sudo systemctl restart {service_name}") # Safe default
            # In a real scenario, this might be: "sudo systemctl restart {service_name}"
            # Or a script: "/opt/scripts/restart_{service_name}.sh"

            command_to_run = restart_command_template.format(service_name=service_name)

            logger.info(f"Attempting to restart service '{service_name}' with command: {command_to_run}")
            try:
                # Simulate execution for safety in testing environment
                # In a real environment, you'd use subprocess.run or similar
                if command_to_run.startswith("echo"): # Safe simulation
                    process = subprocess.Popen(command_to_run, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate(timeout=15)
                    logger.info(f"Simulated restart stdout: {stdout.decode()}")
                    if stderr:
                        logger.error(f"Simulated restart stderr: {stderr.decode()}")

                    # Simulate check after restart
                    time.sleep(1) # Give a moment "for service to come up"

                    # For testing, assume it worked if command was 'echo'
                    return {"status": "success", "action_taken": f"Simulated restart of {service_name}", "details": f"Command: {command_to_run}"}

                else: # Placeholder for actual execution
                     logger.warning(f"Actual execution of '{command_to_run}' skipped in this test environment.")
                     return {"status": "skipped_execution", "action_taken": f"Execution of {command_to_run} for {service_name}", "details":"Actual command execution is typically disabled in basic tests."}

            except subprocess.TimeoutExpired:
                logger.error(f"Timeout restarting service {service_name} with command: {command_to_run}")
                return {"status": "failed", "action_taken": f"Restart {service_name}", "error_message": "Restart command timed out."}
            except Exception as e:
                logger.error(f"Error restarting service {service_name} with command '{command_to_run}': {e}")
                return {"status": "failed", "action_taken": f"Restart {service_name}", "error_message": str(e)}
    """
    # You would need to add this class to your alg911.catana-ai/self_healing/plugins/basic_plugins.py

    recovery_manager = RecoveryManager()

    if not recovery_manager.recovery_plugins:
        logger.warning(
            "No recovery plugins were loaded. Ensure 'basic_plugins.py' is populated with recovery plugins and they are correctly referenced in 'self_healing_config.py'."
        )
        logger.warning(
            "Example dummy recovery plugins are commented out in the __main__ section of recovery.py."
        )
    else:
        logger.info(
            f"Available recovery plugins: {list(recovery_manager.recovery_plugins.keys())}"
        )

        # Simulate diagnosed issues (replace with actual data from IssueDiagnoser)
        simulated_issues = [
            {
                "issue_type": "HTTP_SERVICE_ERROR",
                "severity": "critical",
                "details": "Connection refused",
                "target_id": "katana_api",  # This target_id must exist in self_healing_config.MONITORED_TARGETS
                "diagnosed_by": "HttpStatusIssueDiagnoser",
                "timestamp": "sometime_ago",
            },
            {
                "issue_type": "PROCESS_NOT_RUNNING",
                "severity": "critical",
                "details": "Process katana_agent.py not found",
                "target_id": "katana_main_process",  # Must exist in config
                "diagnosed_by": "ProcessNotRunningDiagnoser",
                "timestamp": "sometime_ago",
            },
            {
                "issue_type": "CRITICAL_LOG_PATTERN_DETECTED",
                "severity": "warning",
                "details": "Found CRITICAL pattern in events.log",
                "target_id": "katana_events_log",  # Must exist in config
                "diagnosed_by": "LogPatternDiagnoser",
                "timestamp": "sometime_ago",
            },
        ]
        # Ensure MONITORED_TARGETS in self_healing_config.py has 'recovery_plugins' for these target_ids.
        # Example for katana_api in config:
        # "katana_api": {
        #     ...
        #     "recovery_plugins": [
        #         {"plugin": "ServiceRestartRecovery", "config": {"service_name": "katana_api_service_name_placeholder"}}
        #     ]
        # }

        logger.info("\n--- Attempting recoveries for simulated issues ---")
        recovery_results = recovery_manager.attempt_all_recoveries(simulated_issues)
        if recovery_results:
            for result in recovery_results:
                logger.info(f"Recovery Result: {result}")
        else:
            logger.info(
                "No recovery actions were attempted or no results returned (check plugin loading and issue matching)."
            )

    print(
        f"RecoveryManager testing complete. Check logs at: {config.LOG_FILE_PATH if hasattr(config, 'LOG_FILE_PATH') else 'self_healing.log'}"
    )
