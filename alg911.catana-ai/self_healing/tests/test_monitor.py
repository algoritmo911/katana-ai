import unittest
from unittest.mock import patch, MagicMock

# Ensure imports work correctly from the test directory.
# This might require adjusting PYTHONPATH or running tests as a module.
# For simplicity, assuming direct import if structure allows or PYTHONPATH is set.
# from ..monitor import ServiceMonitor # If tests are run as module from parent of self_healing
# from ..plugin_interface import MonitoringPlugin # Same as above
# from .. import self_healing_config as SUT_config # SUT: System Under Test

# To run standalone or if above doesn't work due to pathing in test runner:
# Add self_healing parent to path if necessary for your test environment
import sys
import os
# Construct the path to the 'alg911.catana-ai' directory
# This assumes tests are in 'alg911.catana-ai/self_healing/tests'
# and 'alg911.catana-ai' is the project root relative to which module paths are resolved.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from self_healing.monitor import ServiceMonitor
from self_healing.plugin_interface import MonitoringPlugin
from self_healing import self_healing_config as SUT_config
from self_healing.self_healing_logger import logger

# Disable logging for tests to keep output clean, or configure a test logger
logger.setLevel("CRITICAL")


class MockMonitoringPlugin(MonitoringPlugin):
    def __init__(self, name="MockMonitor", health_status="ok", details="Mock good health"):
        self._name = name
        self.health_status = health_status
        self.details = details
        self.check_health_called_with_config = None

    def get_name(self) -> str:
        return self._name

    def check_health(self, config: dict) -> dict:
        self.check_health_called_with_config = config
        return {"status": self.health_status, "details": self.details, "config_received": config}


class TestServiceMonitor(unittest.TestCase):

    def setUp(self):
        # Store original config and plugin loader to restore after tests
        self.original_monitored_targets = SUT_config.MONITORED_TARGETS
        self.original_load_plugin_class = ServiceMonitor._load_plugin_class

    def tearDown(self):
        # Restore original configurations
        SUT_config.MONITORED_TARGETS = self.original_monitored_targets
        ServiceMonitor._load_plugin_class = self.original_load_plugin_class
        # Clear any potentially loaded plugins in a shared ServiceMonitor instance if it were a singleton (not the case here)

    @patch('self_healing.monitor.importlib.import_module')
    def test_load_plugins_from_config_success(self, mock_import_module):
        # Mock the dynamic import and class instantiation
        mock_plugin_instance = MockMonitoringPlugin(name="TestHttpMonitor")
        mock_plugin_class = MagicMock(return_value=mock_plugin_instance)
        mock_plugin_class.__bases__ = (MonitoringPlugin,) # Make it look like a subclass

        # import_module returns a module object, getattr on that returns the class
        mock_module = MagicMock()
        mock_module.TestHttpMonitor = mock_plugin_class
        mock_import_module.return_value = mock_module

        # Configure MONITORED_TARGETS for this test
        SUT_config.MONITORED_TARGETS = {
            "test_service_http": {
                "enabled": True,
                "plugin": "TestHttpMonitor", # Class name to load
                "config": {"url": "http://test.com"},
                "diagnostic_plugins": [], "recovery_plugins": []
            }
        }

        monitor = ServiceMonitor() # This will call _load_plugins_from_config

        self.assertIn("TestHttpMonitor", monitor.monitoring_plugins)
        self.assertIsInstance(monitor.monitoring_plugins["TestHttpMonitor"], MockMonitoringPlugin)
        # Check if import_module was called correctly (module path depends on ServiceMonitor._load_plugins_from_config logic)
        # Example: "self_healing.plugins.basic_plugins"
        expected_module_path = f"self_healing.plugins.basic_plugins"
        mock_import_module.assert_called_with(expected_module_path)
        mock_plugin_class.assert_called_once() # Ensure plugin was instantiated

    @patch('self_healing.monitor.importlib.import_module')
    def test_load_plugins_from_config_disabled_target(self, mock_import_module):
        SUT_config.MONITORED_TARGETS = {
            "disabled_service": {
                "enabled": False, # Key: this service is disabled
                "plugin": "SomeDisabledMonitor",
                "config": {}, "diagnostic_plugins": [], "recovery_plugins": []
            }
        }
        monitor = ServiceMonitor()
        self.assertEqual(len(monitor.monitoring_plugins), 0)
        mock_import_module.assert_not_called()

    @patch('self_healing.monitor.importlib.import_module')
    def test_load_plugins_failure_import_error(self, mock_import_module):
        mock_import_module.side_effect = ImportError("Test Import Error")
        SUT_config.MONITORED_TARGETS = {
            "failing_service": {
                "enabled": True, "plugin": "NonExistentMonitor",
                "config": {}, "diagnostic_plugins": [], "recovery_plugins": []
            }
        }
        monitor = ServiceMonitor()
        self.assertEqual(len(monitor.monitoring_plugins), 0)
        # Check logs for error message if logger was not disabled/mocked

    def test_run_all_checks_no_plugins_loaded(self):
        # Ensure MONITORED_TARGETS is empty or refers to plugins that won't load
        SUT_config.MONITORED_TARGETS = {}
        monitor = ServiceMonitor() # Will load 0 plugins
        results = monitor.run_all_checks()
        self.assertEqual(results, {})

    def test_run_all_checks_with_mock_plugin(self):
        # Setup ServiceMonitor with a manually inserted mock plugin
        # This bypasses the dynamic loading for this specific test, focusing on run_all_checks logic
        monitor = ServiceMonitor() # Initialize first (might load real plugins if config points to them)

        # Clear any auto-loaded plugins and insert our mock
        monitor.monitoring_plugins = {}
        mock_plugin = MockMonitoringPlugin(name="MyMockChecker", health_status="error", details="Simulated failure")
        monitor.monitoring_plugins["MyMockChecker"] = mock_plugin

        # Configure MONITORED_TARGETS to use this mock plugin
        target_id = "mocked_target"
        mock_target_config = {"url": "http://mock.service", "timeout": 5}
        SUT_config.MONITORED_TARGETS = {
            target_id: {
                "enabled": True,
                "plugin": "MyMockChecker", # Name of our mock plugin
                "config": mock_target_config,
                "diagnostic_plugins": [], "recovery_plugins": []
            }
        }

        results = monitor.run_all_checks()

        self.assertIn(target_id, results)
        self.assertEqual(len(results[target_id]), 1)

        health_data = results[target_id][0]
        self.assertEqual(health_data["status"], "error")
        self.assertEqual(health_data["details"], "Simulated failure")
        self.assertEqual(health_data["target_id"], target_id)
        self.assertEqual(health_data["monitor_name"], "MyMockChecker")
        self.assertEqual(mock_plugin.check_health_called_with_config, mock_target_config)
        self.assertIn("timestamp", health_data)

    def test_run_all_checks_plugin_exception(self):
        monitor = ServiceMonitor()
        monitor.monitoring_plugins = {}

        mock_plugin_instance = MockMonitoringPlugin(name="FaultyPlugin")
        # Make the plugin's check_health raise an exception
        mock_plugin_instance.check_health = MagicMock(side_effect=Exception("Plugin Died"))
        monitor.monitoring_plugins["FaultyPlugin"] = mock_plugin_instance

        target_id = "faulty_service"
        SUT_config.MONITORED_TARGETS = {
            target_id: {
                "enabled": True, "plugin": "FaultyPlugin", "config": {},
                "diagnostic_plugins": [], "recovery_plugins": []
            }
        }

        results = monitor.run_all_checks()
        self.assertIn(target_id, results)
        self.assertEqual(len(results[target_id]), 1)
        health_data = results[target_id][0]

        self.assertEqual(health_data["status"], "error")
        self.assertEqual(health_data["error_message"], "Exception occurred during check_health call.")
        self.assertEqual(health_data["details"], "Exception occurred during check_health call.") # Check monitor.py for exact message
        self.assertEqual(health_data["target_id"], target_id)
        self.assertEqual(health_data["monitor_name"], "FaultyPlugin")


if __name__ == '__main__':
    unittest.main(verbosity=2)
