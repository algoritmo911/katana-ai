import importlib
from typing import Any, Dict, List, Type

from . import self_healing_config as config
from .self_healing_logger import logger
from .plugin_interface import DiagnosticPlugin

class IssueDiagnoser:
    """
    Manages and executes diagnostic plugins to analyze monitoring data and identify issues.
    """

    def __init__(self):
        self.diagnostic_plugins: Dict[str, DiagnosticPlugin] = {}
        self._load_plugins_from_config() # Similar to ServiceMonitor, load diagnostic plugins

    def _load_plugin_class(self, module_name: str, class_name: str) -> Type[DiagnosticPlugin] | None:
        """Dynamically loads a diagnostic plugin class from a given module."""
        try:
            module = importlib.import_module(module_name)
            plugin_class = getattr(module, class_name)
            if not issubclass(plugin_class, DiagnosticPlugin):
                logger.error(f"Plugin class {class_name} from {module_name} does not inherit from DiagnosticPlugin.")
                return None
            return plugin_class
        except ImportError:
            logger.error(f"Failed to import module {module_name} for diagnostic plugin {class_name}.")
            return None
        except AttributeError:
            logger.error(f"Class {class_name} not found in module {module_name} for diagnostics.")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading diagnostic plugin {module_name}.{class_name}: {e}")
            return None

    def _load_plugins_from_config(self):
        """
        Loads diagnostic plugins based on the MONITORED_TARGETS configuration.
        Assumes diagnostic plugins are also located in '.plugins.basic_plugins'.
        """
        logger.info("Loading diagnostic plugins...")
        plugin_module_name_base = ".plugins.basic_plugins" # Relative to current package 'self_healing'

        unique_plugin_types_to_load: Dict[str, Dict[str, Any]] = {}

        for target_id, target_config in config.MONITORED_TARGETS.items():
            if not target_config.get("enabled", False):
                continue

            diagnostic_plugin_configs = target_config.get("diagnostic_plugins", [])
            for plugin_entry in diagnostic_plugin_configs:
                plugin_class_name = plugin_entry.get("plugin")
                if not plugin_class_name:
                    logger.warning(f"No 'plugin' name specified in diagnostic_plugins for target '{target_id}'. Skipping entry: {plugin_entry}")
                    continue

                if plugin_class_name not in unique_plugin_types_to_load:
                    unique_plugin_types_to_load[plugin_class_name] = {
                        "module_name": plugin_module_name_base, # Assuming all basic diagnostic plugins are here
                        "class_name": plugin_class_name
                    }

        for plugin_name, plugin_info in unique_plugin_types_to_load.items():
            module_full_name = f"{__package__}{plugin_info['module_name']}"
            plugin_class = self._load_plugin_class(module_full_name, plugin_info['class_name'])
            if plugin_class:
                try:
                    self.diagnostic_plugins[plugin_name] = plugin_class()
                    logger.info(f"Successfully loaded and instantiated diagnostic plugin: {plugin_name}")
                except Exception as e:
                    logger.error(f"Failed to instantiate diagnostic plugin {plugin_name}: {e}")

        logger.info(f"Loaded {len(self.diagnostic_plugins)} unique diagnostic plugin types.")


    def run_diagnostics(self, all_monitor_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Runs appropriate diagnostic plugins on the collected monitoring data.

        Args:
            all_monitor_data: A dictionary where keys are target_ids and values are lists of
                              health data dictionaries from the ServiceMonitor.

        Returns:
            A list of all diagnosed issues found across all targets.
        """
        all_diagnosed_issues: List[Dict[str, Any]] = []
        logger.info("Starting diagnostics process...")

        for target_id, monitor_data_list in all_monitor_data.items():
            if not monitor_data_list: # Should not happen if monitor ran, but good check
                logger.debug(f"No monitoring data for target '{target_id}'. Skipping diagnostics for it.")
                continue

            target_config = config.MONITORED_TARGETS.get(target_id)
            if not target_config or not target_config.get("enabled", False):
                logger.debug(f"Target '{target_id}' not configured for diagnostics or is disabled. Skipping.")
                continue

            diagnostic_plugin_configs = target_config.get("diagnostic_plugins", [])
            if not diagnostic_plugin_configs:
                logger.debug(f"No diagnostic plugins configured for target '{target_id}'.")
                continue

            logger.debug(f"Running diagnostics for target '{target_id}' which has {len(monitor_data_list)} data points.")

            for plugin_config_entry in diagnostic_plugin_configs:
                plugin_name = plugin_config_entry.get("plugin")
                if not plugin_name:
                    logger.warning(f"Diagnostic plugin entry for '{target_id}' is missing 'plugin' name. Skipping.")
                    continue

                diagnostic_plugin_instance = self.diagnostic_plugins.get(plugin_name)
                if not diagnostic_plugin_instance:
                    logger.error(f"Diagnostic plugin '{plugin_name}' for target '{target_id}' not found or loaded. Skipping diagnosis with this plugin.")
                    continue

                plugin_specific_config = plugin_config_entry.get("config", {})
                logger.debug(f"Using diagnostic plugin '{diagnostic_plugin_instance.get_name()}' for '{target_id}' with config: {plugin_specific_config}")

                try:
                    # Pass all monitor data for the current target to the diagnose method
                    # The plugin itself can decide if it cares about one or more data points
                    diagnosed_issues = diagnostic_plugin_instance.diagnose(monitor_data_list, plugin_specific_config)

                    if diagnosed_issues:
                        logger.info(f"Plugin '{diagnostic_plugin_instance.get_name()}' found {len(diagnosed_issues)} issue(s) for target '{target_id}'.")
                        for issue in diagnosed_issues:
                            # Enrich issue with context if not already present
                            issue.setdefault("target_id", target_id)
                            issue.setdefault("diagnosed_by", diagnostic_plugin_instance.get_name())
                            issue.setdefault("timestamp", logger.handlers[0].formatter.formatTime(logger.makeRecord("",0,"","",0,"",(),None,None)))
                            all_diagnosed_issues.append(issue)
                            logger.debug(f"Diagnosed issue for '{target_id}': {issue}")
                    else:
                        logger.debug(f"Plugin '{diagnostic_plugin_instance.get_name()}' found no issues for target '{target_id}'.")

                except Exception as e:
                    logger.error(f"Error during diagnosis for '{target_id}' with plugin '{diagnostic_plugin_instance.get_name()}': {e}", exc_info=True)
                    # Optionally, create a generic issue indicating diagnostic failure
                    all_diagnosed_issues.append({
                        "issue_type": "DIAGNOSTIC_ERROR",
                        "severity": "error",
                        "details": f"Exception in plugin {diagnostic_plugin_instance.get_name()}: {str(e)}",
                        "target_id": target_id,
                        "diagnosed_by": diagnostic_plugin_instance.get_name(),
                        "timestamp": logger.handlers[0].formatter.formatTime(logger.makeRecord("",0,"","",0,"",(),None,None))
                    })

        logger.info(f"Finished diagnostics. Found a total of {len(all_diagnosed_issues)} issues across all targets.")
        return all_diagnosed_issues

if __name__ == "__main__":
    logger.info("Starting IssueDiagnoser direct test...")

    # This test requires:
    # 1. self_healing_config.py to be set up.
    # 2. plugin_interface.py to define DiagnosticPlugin.
    # 3. plugins/basic_plugins.py to contain actual diagnostic plugin classes
    #    referenced in self_healing_config.py (e.g., HttpStatusIssueDiagnoser, LogPatternDiagnoser).

    # Mockup of basic_plugins.py for standalone testing (Diagnostic parts):
    """
    from ..plugin_interface import DiagnosticPlugin
    from ..self_healing_logger import logger # Assuming logger is accessible

    class HttpStatusIssueDiagnoser(DiagnosticPlugin):
        def get_name(self) -> str: return "HttpStatusIssueDiagnoser"
        def diagnose(self, monitor_data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
            issues = []
            critical_codes = config.get("critical_status_codes", [500, 503])
            for data_point in monitor_data:
                if data_point.get("monitor_name") == "HttpAvailabilityMonitor" and data_point.get("status") == "error":
                    # Simplistic: any error from HttpAvailabilityMonitor is an issue
                    # A real one would check status_code if available in data_point
                    issues.append({
                        "issue_type": "HTTP_SERVICE_ERROR",
                        "severity": "critical" if data_point.get("http_status_code") in critical_codes else "warning",
                        "details": data_point.get("error_message", "Unknown HTTP error"),
                        "source_data": data_point
                    })
                elif data_point.get("monitor_name") == "HttpAvailabilityMonitor" and data_point.get("http_status_code") in critical_codes :
                     issues.append({
                        "issue_type": "HTTP_CRITICAL_STATUS_CODE",
                        "severity": "critical",
                        "details": f"HTTP status {data_point.get('http_status_code')} received.",
                        "source_data": data_point
                    })
            return issues

    class ProcessNotRunningDiagnoser(DiagnosticPlugin):
        def get_name(self) -> str: return "ProcessNotRunningDiagnoser"
        def diagnose(self, monitor_data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
            issues = []
            for data_point in monitor_data:
                if data_point.get("monitor_name") == "ProcessRunningMonitor":
                    if data_point.get("status") == "error" or not data_point.get("pids"):
                        issues.append({
                            "issue_type": "PROCESS_NOT_RUNNING",
                            "severity": "critical",
                            "details": f"Process matching '{data_point.get('process_name')}' not found or monitor error.",
                            "source_data": data_point
                        })
            return issues

    class LogPatternDiagnoser(DiagnosticPlugin):
        def get_name(self) -> str: return "LogPatternDiagnoser"
        def diagnose(self, monitor_data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
            issues = []
            threshold = config.get("critical_pattern_threshold", 1)
            for data_point in monitor_data:
                if data_point.get("monitor_name") == "LogFileMonitor":
                    if data_point.get("status") == "warning" or data_point.get("status") == "error": # Monitor might flag these
                        if len(data_point.get("found_patterns", [])) >= threshold:
                            issues.append({
                                "issue_type": "CRITICAL_LOG_PATTERN_DETECTED",
                                "severity": "warning", # Could be critical depending on patterns
                                "details": f"Found patterns: {data_point.get('found_patterns')} in {data_point.get('log_file')}",
                                "source_data": data_point
                            })
            return issues
    """
    # You would need to add these classes to your alg911.catana-ai/self_healing/plugins/basic_plugins.py

    diagnoser = IssueDiagnoser()

    if not diagnoser.diagnostic_plugins:
        logger.warning("No diagnostic plugins were loaded. Ensure 'basic_plugins.py' is populated with diagnostic plugins and they are correctly referenced in 'self_healing_config.py'.")
        logger.warning("Example dummy diagnostic plugins are commented out in the __main__ section of diagnostics.py.")
    else:
        logger.info(f"Available diagnostic plugins: {list(diagnoser.diagnostic_plugins.keys())}")

        # Simulate monitor data (replace with actual data from ServiceMonitor if testing together)
        simulated_monitor_data = {
            "katana_api": [
                {"status": "error", "error_message": "Connection refused", "url": "http://localhost:5001/api/v1/health", "target_id": "katana_api", "monitor_name": "HttpAvailabilityMonitor", "http_status_code": None, "timestamp": "sometime"},
                {"status": "ok", "response_time_ms": 200, "url": "http://localhost:5001/api/v1/some_other_endpoint", "target_id": "katana_api", "monitor_name": "HttpAvailabilityMonitor", "http_status_code": 200, "timestamp": "sometime"}
            ],
            "katana_main_process": [
                {"status": "ok", "process_name": "katana_agent.py", "pids": [123], "target_id": "katana_main_process", "monitor_name": "ProcessRunningMonitor", "timestamp": "sometime"}
            ],
             "katana_events_log": [
                {"status": "warning", "log_file": "path/to/events.log", "found_patterns": ["CRITICAL"], "lines_matched": 1, "target_id": "katana_events_log", "monitor_name": "LogFileMonitor", "timestamp": "sometime"}
            ]
        }

        # Simulate a case where HttpAvailabilityMonitor actually reports a 503
        simulated_monitor_data_critical_http = {
             "katana_api": [
                {"status": "ok", "response_time_ms": 200, "url": "http://localhost:5001/api/v1/health", "target_id": "katana_api", "monitor_name": "HttpAvailabilityMonitor", "http_status_code": 503, "timestamp": "sometime"}
            ]
        }


        logger.info("\n--- Running diagnostics on simulated data ---")
        diagnosed = diagnoser.run_diagnostics(simulated_monitor_data)
        if diagnosed:
            for issue in diagnosed:
                logger.info(f"Diagnosed Issue: {issue}")
        else:
            logger.info("No issues diagnosed from simulated data.")

        logger.info("\n--- Running diagnostics on critical HTTP status data ---")
        diagnosed_critical = diagnoser.run_diagnostics(simulated_monitor_data_critical_http)
        if diagnosed_critical:
            for issue in diagnosed_critical:
                logger.info(f"Diagnosed Issue (Critical HTTP): {issue}")
        else:
            logger.info("No issues diagnosed from critical HTTP data.")


    print(f"Diagnoser testing complete. Check logs at: {config.LOG_FILE_PATH if hasattr(config, 'LOG_FILE_PATH') else 'self_healing.log'}")
