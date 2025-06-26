import importlib
from typing import Any, Dict, List, Type

from . import self_healing_config as config
from .self_healing_logger import logger
from .plugin_interface import MonitoringPlugin

class ServiceMonitor:
    """
    Manages and executes monitoring plugins to gather health data about various system components.
    """

    def __init__(self):
        self.monitoring_plugins: Dict[str, MonitoringPlugin] = {}
        self._load_plugins_from_config()

    def _load_plugin_class(self, module_name: str, class_name: str) -> Type[MonitoringPlugin] | None:
        """Dynamically loads a plugin class from a given module."""
        try:
            module = importlib.import_module(module_name)
            plugin_class = getattr(module, class_name)
            if not issubclass(plugin_class, MonitoringPlugin):
                logger.error(f"Plugin class {class_name} from {module_name} does not inherit from MonitoringPlugin.")
                return None
            return plugin_class
        except ImportError:
            logger.error(f"Failed to import module {module_name} for plugin {class_name}.")
            return None
        except AttributeError:
            logger.error(f"Class {class_name} not found in module {module_name}.")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading plugin {module_name}.{class_name}: {e}")
            return None

    def _load_plugins_from_config(self):
        """
        Loads monitoring plugins based on the MONITORED_TARGETS configuration.
        This version assumes plugins are located in '.plugins.basic_plugins'.
        A more robust solution might involve a plugin registration system or scanning a plugin directory.
        """
        logger.info("Loading monitoring plugins...")
        # Simplified plugin loading: assumes plugins are in '.plugins.basic_plugins'
        # and the class name matches the 'plugin' field in config.
        # Example: plugin: "HttpAvailabilityMonitor" -> class HttpAvailabilityMonitor in basic_plugins.py
        plugin_module_name_base = ".plugins.basic_plugins" # Relative to current package 'self_healing'

        unique_plugin_types_to_load: Dict[str, Dict[str, Any]] = {}

        for target_id, target_config in config.MONITORED_TARGETS.items():
            if not target_config.get("enabled", False):
                logger.debug(f"Target '{target_id}' is disabled. Skipping plugin loading for it.")
                continue

            plugin_class_name = target_config.get("plugin")
            if not plugin_class_name:
                logger.warning(f"No 'plugin' specified for target '{target_id}'. Skipping.")
                continue

            # Store the first configuration encountered for a given plugin type.
            # This means all instances of "HttpAvailabilityMonitor" will use the same plugin class.
            if plugin_class_name not in unique_plugin_types_to_load:
                 unique_plugin_types_to_load[plugin_class_name] = {
                    "module_name": plugin_module_name_base, # Modify if plugins are in different modules
                    "class_name": plugin_class_name
                }

        for plugin_name, plugin_info in unique_plugin_types_to_load.items():
            module_full_name = f"{__package__}{plugin_info['module_name']}" # e.g., self_healing.plugins.basic_plugins
            plugin_class = self._load_plugin_class(module_full_name, plugin_info['class_name'])
            if plugin_class:
                try:
                    self.monitoring_plugins[plugin_name] = plugin_class()
                    logger.info(f"Successfully loaded and instantiated monitoring plugin: {plugin_name}")
                except Exception as e:
                    logger.error(f"Failed to instantiate plugin {plugin_name}: {e}")

        logger.info(f"Loaded {len(self.monitoring_plugins)} unique monitoring plugin types.")


    def run_all_checks(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Runs all configured and enabled health checks.

        Returns:
            A dictionary where keys are target_ids and values are a list of health data dicts
            (though typically one for monitoring, could be more if a target has multiple checks).
        """
        all_health_data: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("Starting all monitoring checks...")

        for target_id, target_config in config.MONITORED_TARGETS.items():
            if not target_config.get("enabled", False):
                logger.debug(f"Monitoring for target '{target_id}' is disabled. Skipping.")
                continue

            plugin_name = target_config.get("plugin")
            if not plugin_name:
                logger.warning(f"No plugin specified for enabled target '{target_id}'. Cannot monitor.")
                continue

            plugin_instance = self.monitoring_plugins.get(plugin_name)
            if not plugin_instance:
                logger.error(f"Monitoring plugin '{plugin_name}' for target '{target_id}' not found or loaded. Skipping check.")
                all_health_data.setdefault(target_id, []).append({
                    "status": "error",
                    "error_message": f"Plugin {plugin_name} not loaded",
                    "target_id": target_id,
                    "monitor_name": plugin_name
                })
                continue

            monitor_specific_config = target_config.get("config", {})
            logger.debug(f"Running check for '{target_id}' using plugin '{plugin_instance.get_name()}' with config: {monitor_specific_config}")

            try:
                health_data = plugin_instance.check_health(monitor_specific_config)
                # Add context to the health data
                health_data["target_id"] = target_id
                health_data["monitor_name"] = plugin_instance.get_name()
                health_data["timestamp"] = logger.handlers[0].formatter.formatTime(logger.makeRecord("",0,"","",0,"",(),None,None)) # Get timestamp

                all_health_data.setdefault(target_id, []).append(health_data)
                logger.debug(f"Health data for '{target_id}': {health_data}")
            except Exception as e:
                logger.error(f"Error during health check for '{target_id}' with plugin '{plugin_instance.get_name()}': {e}", exc_info=True)
                all_health_data.setdefault(target_id, []).append({
                    "status": "error",
                    "error_message": str(e),
                    "details": "Exception occurred during check_health call.",
                    "target_id": target_id,
                    "monitor_name": plugin_instance.get_name(),
                    "timestamp": logger.handlers[0].formatter.formatTime(logger.makeRecord("",0,"","",0,"",(),None,None))
                })

        logger.info(f"Finished all monitoring checks. Collected data for {len(all_health_data)} targets.")
        return all_health_data

if __name__ == "__main__":
    # This requires basic_plugins.py to have some dummy plugins for testing
    logger.info("Starting ServiceMonitor direct test...")

    # To test this standalone, we need to ensure that basic_plugins.py exists and
    # contains classes like 'HttpAvailabilityMonitor', 'ProcessRunningMonitor', 'LogFileMonitor'
    # which are defined in self_healing_config.py.
    # For now, this will likely error out or load 0 plugins if basic_plugins.py is empty.

    # Mockup of basic_plugins.py for standalone testing:
    # Create a dummy alg911.catana-ai/self_healing/plugins/basic_plugins.py with:
    """
    from ..plugin_interface import MonitoringPlugin
    import os
    import time

    class HttpAvailabilityMonitor(MonitoringPlugin):
        def get_name(self) -> str: return "HttpAvailabilityMonitor"
        def check_health(self, config: dict) -> dict:
            url = config.get('url', 'http://example.com')
            logger.info(f"HttpAvailabilityMonitor: Checking {url} (simulated)")
            if "bad" in url:
                return {"status": "error", "error_message": "Simulated HTTP error", "url": url}
            return {"status": "ok", "response_time_ms": 120, "url": url}

    class ProcessRunningMonitor(MonitoringPlugin):
        def get_name(self) -> str: return "ProcessRunningMonitor"
        def check_health(self, config: dict) -> dict:
            pname = config.get('process_name_pattern', 'python')
            logger.info(f"ProcessRunningMonitor: Checking for process '{pname}' (simulated)")
            # Simulate check, e.g., always found for testing
            return {"status": "ok", "process_name": pname, "pids": [1234, 5678]}

    class LogFileMonitor(MonitoringPlugin):
        def get_name(self) -> str: return "LogFileMonitor"
        def check_health(self, config: dict) -> dict:
            fpath = config.get('log_file_path', 'dummy.log')
            patterns = config.get('error_patterns', [])
            logger.info(f"LogFileMonitor: Checking '{fpath}' for patterns (simulated)")
            # Simulate finding a pattern
            if "CRITICAL" in patterns:
                 return {"status": "warning", "log_file": fpath, "found_patterns": ["CRITICAL"], "lines_matched": 1}
            return {"status": "ok", "log_file": fpath, "found_patterns": []}
    """
    # You would need to create this file with the content above for the test to run fully.
    # Ensure __init__.py is in the 'plugins' directory.

    monitor = ServiceMonitor()

    if not monitor.monitoring_plugins:
        logger.warning("No monitoring plugins were loaded. Ensure 'basic_plugins.py' is populated and correctly referenced in 'self_healing_config.py'.")
        logger.warning("Example dummy plugins are commented out in the __main__ section of monitor.py.")
    else:
        logger.info(f"Available monitoring plugins: {list(monitor.monitoring_plugins.keys())}")

        all_data = monitor.run_all_checks()
        logger.info("\n--- Results of all checks ---")
        for target_id, data_list in all_data.items():
            logger.info(f"Target: {target_id}")
            for data_point in data_list:
                logger.info(f"  Data: {data_point}")
        logger.info("--- End of results ---")

    print(f"Monitor testing complete. Check logs at: {config.LOG_FILE_PATH if hasattr(config, 'LOG_FILE_PATH') else 'self_healing.log'}")
