import unittest
from unittest.mock import patch, MagicMock

import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from self_healing.recovery import RecoveryManager
from self_healing.plugin_interface import RecoveryPlugin
from self_healing import self_healing_config as SUT_config
from self_healing.self_healing_logger import logger

logger.setLevel("CRITICAL")


class MockRecoveryPlugin(RecoveryPlugin):
    def __init__(self, name="MockRecoverer", can_recover_response=True, recovery_status="success", action_taken="Mock action"):
        self._name = name
        self.can_recover_response = can_recover_response
        self.recovery_status = recovery_status
        self.action_taken = action_taken
        self.can_recover_called_with_issue = None
        self.attempt_recovery_called_with_issue = None
        self.attempt_recovery_called_with_config = None

    def get_name(self) -> str:
        return self._name

    def can_recover(self, issue: dict) -> bool:
        self.can_recover_called_with_issue = issue
        return self.can_recover_response

    def attempt_recovery(self, issue: dict, config: dict) -> dict:
        self.attempt_recovery_called_with_issue = issue
        self.attempt_recovery_called_with_config = config
        return {"status": self.recovery_status, "action_taken": self.action_taken, "recovered_by_mock": True}


class TestRecoveryManager(unittest.TestCase):

    def setUp(self):
        self.original_monitored_targets = SUT_config.MONITORED_TARGETS
        # Similar to other managers, if dynamic loading is complex, mock it or parts of it.

    def tearDown(self):
        SUT_config.MONITORED_TARGETS = self.original_monitored_targets

    @patch('self_healing.recovery.importlib.import_module')
    def test_load_plugins_from_config_success(self, mock_import_module):
        mock_plugin_instance = MockRecoveryPlugin(name="TestServiceRestarter")
        mock_plugin_class = MagicMock(return_value=mock_plugin_instance)
        mock_plugin_class.__bases__ = (RecoveryPlugin,)

        mock_module = MagicMock()
        mock_module.TestServiceRestarter = mock_plugin_class
        mock_import_module.return_value = mock_module

        SUT_config.MONITORED_TARGETS = {
            "test_service_for_recovery": {
                "enabled": True, "plugin": "AnyMonitor", "config": {},
                "diagnostic_plugins": [],
                "recovery_plugins": [
                    {"plugin": "TestServiceRestarter", "config": {"command": "restart.sh"}}
                ]
            }
        }

        manager = RecoveryManager() # Triggers plugin loading

        self.assertIn("TestServiceRestarter", manager.recovery_plugins)
        self.assertIsInstance(manager.recovery_plugins["TestServiceRestarter"], MockRecoveryPlugin)
        expected_module_path = f"self_healing.plugins.basic_plugins"
        mock_import_module.assert_called_with(expected_module_path)
        mock_plugin_class.assert_called_once()

    def test_attempt_all_recoveries_no_issues(self):
        manager = RecoveryManager()
        manager.recovery_plugins = {} # Ensure no plugins interfere
        SUT_config.MONITORED_TARGETS = {}

        results = manager.attempt_all_recoveries([]) # Empty list of issues
        self.assertEqual(results, [])

    def test_attempt_all_recoveries_with_mock_plugin_success(self):
        manager = RecoveryManager()
        manager.recovery_plugins = {} # Clear auto-loaded

        mock_plugin = MockRecoveryPlugin(name="MyMockRecoverer", can_recover_response=True, recovery_status="success")
        manager.recovery_plugins["MyMockRecoverer"] = mock_plugin

        target_id = "server_gamma"
        diagnosed_issue = {"target_id": target_id, "issue_type": "SERVICE_DOWN", "severity": "critical"}

        recovery_plugin_config_entry = {"plugin": "MyMockRecoverer", "config": {"script_path": "/opt/recover.sh"}}
        SUT_config.MONITORED_TARGETS = {
            target_id: {
                "enabled": True, "plugin": "AnyMonitor", "config": {},
                "diagnostic_plugins": [],
                "recovery_plugins": [recovery_plugin_config_entry]
            }
        }

        recovery_results = manager.attempt_all_recoveries([diagnosed_issue])

        self.assertEqual(len(recovery_results), 1)
        result = recovery_results[0]

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["recovered_by_mock"])
        self.assertEqual(result["target_id"], target_id) # Enriched by manager
        self.assertEqual(result["recovered_by"], "MyMockRecoverer") # Enriched
        self.assertIn("timestamp", result) # Enriched

        self.assertEqual(mock_plugin.can_recover_called_with_issue, diagnosed_issue)
        self.assertEqual(mock_plugin.attempt_recovery_called_with_issue, diagnosed_issue)
        self.assertEqual(mock_plugin.attempt_recovery_called_with_config, recovery_plugin_config_entry["config"])

    def test_attempt_all_recoveries_plugin_cannot_recover(self):
        manager = RecoveryManager()
        manager.recovery_plugins = {}

        mock_plugin = MockRecoveryPlugin(name="SelectiveRecoverer", can_recover_response=False) # Plugin says it cannot recover
        manager.recovery_plugins["SelectiveRecoverer"] = mock_plugin

        target_id = "service_delta"
        diagnosed_issue = {"target_id": target_id, "issue_type": "RARE_ISSUE", "severity": "warning"}

        SUT_config.MONITORED_TARGETS = {
            target_id: {
                "enabled": True, "plugin": "AnyMonitor", "config": {},
                "diagnostic_plugins": [],
                "recovery_plugins": [{"plugin": "SelectiveRecoverer", "config": {}}]
            }
        }

        recovery_results = manager.attempt_all_recoveries([diagnosed_issue])
        self.assertEqual(len(recovery_results), 0) # No recovery attempt should be made or logged as a result by this plugin
        self.assertEqual(mock_plugin.can_recover_called_with_issue, diagnosed_issue)
        self.assertIsNone(mock_plugin.attempt_recovery_called_with_issue) # attempt_recovery should not be called

    def test_attempt_all_recoveries_plugin_fails_recovery(self):
        manager = RecoveryManager()
        manager.recovery_plugins = {}

        mock_plugin = MockRecoveryPlugin(name="FaultyRecoverer", can_recover_response=True, recovery_status="failed")
        manager.recovery_plugins["FaultyRecoverer"] = mock_plugin

        target_id = "unlucky_service"
        diagnosed_issue = {"target_id": target_id, "issue_type": "DB_CONNECTION_LOST", "severity": "critical"}

        SUT_config.MONITORED_TARGETS = {
            target_id: {
                "enabled": True, "plugin": "AnyMonitor", "config": {},
                "diagnostic_plugins": [],
                "recovery_plugins": [{"plugin": "FaultyRecoverer", "config": {}}]
            }
        }

        recovery_results = manager.attempt_all_recoveries([diagnosed_issue])
        self.assertEqual(len(recovery_results), 1)
        result = recovery_results[0]
        self.assertEqual(result["status"], "failed")

    def test_attempt_all_recoveries_plugin_exception(self):
        manager = RecoveryManager()
        manager.recovery_plugins = {}

        mock_plugin_instance = MockRecoveryPlugin(name="ExplodingRecoverer")
        mock_plugin_instance.attempt_recovery = MagicMock(side_effect=Exception("Recovery Exploded"))
        manager.recovery_plugins["ExplodingRecoverer"] = mock_plugin_instance

        target_id = "fragile_service"
        diagnosed_issue = {"target_id": target_id, "issue_type": "KERNEL_PANIC_SIM", "severity": "critical"}

        SUT_config.MONITORED_TARGETS = {
            target_id: {
                "enabled": True, "plugin": "AnyMonitor", "config": {},
                "diagnostic_plugins": [],
                "recovery_plugins": [{"plugin": "ExplodingRecoverer", "config": {}}]
            }
        }

        recovery_results = manager.attempt_all_recoveries([diagnosed_issue])
        self.assertEqual(len(recovery_results), 1)
        result = recovery_results[0]
        self.assertEqual(result["status"], "error")
        self.assertIn("Exception in plugin: Recovery Exploded", result["error_message"])
        self.assertEqual(result["recovered_by"], "ExplodingRecoverer")

    def test_attempt_all_recoveries_no_recovery_plugin_for_target(self):
        manager = RecoveryManager()
        manager.recovery_plugins = {} # No plugins loaded

        target_id = "unmanaged_target"
        diagnosed_issue = {"target_id": target_id, "issue_type": "SOME_PROBLEM", "severity": "critical"}

        # Target is configured, but has no recovery_plugins list or it's empty
        SUT_config.MONITORED_TARGETS = {
            target_id: {
                "enabled": True, "plugin": "AnyMonitor", "config": {},
                "diagnostic_plugins": [],
                "recovery_plugins": [] # Empty list
            }
        }
        recovery_results = manager.attempt_all_recoveries([diagnosed_issue])
        self.assertEqual(recovery_results, [])

        # Test with recovery_plugins key missing entirely
        SUT_config.MONITORED_TARGETS = {
            target_id: {
                "enabled": True, "plugin": "AnyMonitor", "config": {},
                "diagnostic_plugins": [],
                # "recovery_plugins" key missing
            }
        }
        recovery_results = manager.attempt_all_recoveries([diagnosed_issue])
        self.assertEqual(recovery_results, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
