import unittest
from unittest.mock import patch, MagicMock

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from self_healing.diagnostics import IssueDiagnoser
from self_healing.plugin_interface import DiagnosticPlugin
from self_healing import self_healing_config as SUT_config  # SUT: System Under Test
from self_healing.self_healing_logger import logger

logger.setLevel("CRITICAL")  # Keep test output clean


class MockDiagnosticPlugin(DiagnosticPlugin):
    def __init__(self, name="MockDiagnoser", issues_to_return=None):
        self._name = name
        self.issues_to_return = issues_to_return if issues_to_return is not None else []
        self.diagnose_called_with_data = None
        self.diagnose_called_with_config = None

    def get_name(self) -> str:
        return self._name

    def diagnose(self, monitor_data: list, config: dict) -> list:
        self.diagnose_called_with_data = monitor_data
        self.diagnose_called_with_config = config
        # Return a copy to avoid modification issues if the list is stored and reused
        return [dict(issue) for issue in self.issues_to_return]


class TestIssueDiagnoser(unittest.TestCase):

    def setUp(self):
        self.original_monitored_targets = SUT_config.MONITORED_TARGETS
        # If IssueDiagnoser loads plugins similarly to ServiceMonitor, mock its loader too
        # For now, assuming we might manually insert plugins or mock the config structure.

    def tearDown(self):
        SUT_config.MONITORED_TARGETS = self.original_monitored_targets

    @patch.object(IssueDiagnoser, "_load_plugin_class")
    def test_load_plugins_from_config_success(self, mock_load_plugin_class_method):
        final_mock_instance = MockDiagnosticPlugin(name="TestIssueClassifier")

        MockClassToReturn = MagicMock(spec=DiagnosticPlugin)
        MockClassToReturn.return_value = final_mock_instance

        def side_effect_load_plugin_class(module_name, class_name):
            if class_name == "TestIssueClassifier":
                return MockClassToReturn
            return None

        mock_load_plugin_class_method.side_effect = side_effect_load_plugin_class

        SUT_config.MONITORED_TARGETS = {
            "test_service_for_diag": {
                "enabled": True,
                "plugin": "SomeMonitor",
                "config": {},  # Actual monitor plugin doesn't matter for this test
                "diagnostic_plugins": [
                    {"plugin": "TestIssueClassifier", "config": {"threshold": 0.5}}
                ],
                "recovery_plugins": [],
            }
        }

        diagnoser = IssueDiagnoser()

        self.assertIn("TestIssueClassifier", diagnoser.diagnostic_plugins)
        self.assertIsInstance(
            diagnoser.diagnostic_plugins["TestIssueClassifier"], MockDiagnosticPlugin
        )
        expected_module_name = (
            "self_healing.plugins.basic_plugins"  # From IssueDiagnoser logic
        )
        mock_load_plugin_class_method.assert_any_call(
            expected_module_name, "TestIssueClassifier"
        )
        MockClassToReturn.assert_called_once()

    def test_run_diagnostics_no_monitor_data(self):
        diagnoser = IssueDiagnoser()
        diagnoser.diagnostic_plugins = {}  # Ensure no plugins interfere
        SUT_config.MONITORED_TARGETS = {}  # No targets configured

        results = diagnoser.run_diagnostics({})  # Empty monitor data
        self.assertEqual(results, [])

    def test_run_diagnostics_with_mock_plugin(self):
        diagnoser = IssueDiagnoser()
        diagnoser.diagnostic_plugins = {}  # Clear auto-loaded plugins

        mock_issue = {
            "issue_type": "CPU_HIGH",
            "severity": "warning",
            "details": "CPU at 90%",
        }
        mock_plugin = MockDiagnosticPlugin(
            name="MyMockDiagnoser", issues_to_return=[mock_issue]
        )
        diagnoser.diagnostic_plugins["MyMockDiagnoser"] = mock_plugin

        target_id = "server_alpha"
        monitor_data_for_target = [
            {"target_id": target_id, "monitor_name": "CpuMonitor", "cpu_usage": 0.9}
        ]
        all_monitor_data = {target_id: monitor_data_for_target}

        # Configure target in SUT_config to use this diagnostic plugin
        diag_plugin_config_entry = {
            "plugin": "MyMockDiagnoser",
            "config": {"custom_param": "value"},
        }
        SUT_config.MONITORED_TARGETS = {
            target_id: {
                "enabled": True,
                "plugin": "CpuMonitor",
                "config": {},  # Monitor plugin details don't matter much here
                "diagnostic_plugins": [diag_plugin_config_entry],
                "recovery_plugins": [],
            }
        }

        diagnosed_issues = diagnoser.run_diagnostics(all_monitor_data)

        self.assertEqual(len(diagnosed_issues), 1)
        returned_issue = diagnosed_issues[0]

        self.assertEqual(returned_issue["issue_type"], mock_issue["issue_type"])
        self.assertEqual(returned_issue["severity"], mock_issue["severity"])
        self.assertEqual(returned_issue["details"], mock_issue["details"])
        self.assertEqual(
            returned_issue["target_id"], target_id
        )  # Enriched by diagnoser
        self.assertEqual(returned_issue["diagnosed_by"], "MyMockDiagnoser")  # Enriched
        self.assertIn("timestamp", returned_issue)  # Enriched

        # Check that the mock plugin's diagnose method was called correctly
        self.assertEqual(mock_plugin.diagnose_called_with_data, monitor_data_for_target)
        self.assertEqual(
            mock_plugin.diagnose_called_with_config, diag_plugin_config_entry["config"]
        )

    def test_run_diagnostics_plugin_exception(self):
        diagnoser = IssueDiagnoser()
        diagnoser.diagnostic_plugins = {}

        mock_plugin_instance = MockDiagnosticPlugin(name="CrashingDiagnoser")
        mock_plugin_instance.diagnose = MagicMock(
            side_effect=Exception("Diagnoser Died")
        )
        diagnoser.diagnostic_plugins["CrashingDiagnoser"] = mock_plugin_instance

        target_id = "service_beta"
        monitor_data_for_target = [
            {"target_id": target_id, "monitor_name": "SomeMonitor", "data": "value"}
        ]
        all_monitor_data = {target_id: monitor_data_for_target}

        diag_plugin_config_entry = {"plugin": "CrashingDiagnoser", "config": {}}
        SUT_config.MONITORED_TARGETS = {
            target_id: {
                "enabled": True,
                "plugin": "SomeMonitor",
                "config": {},
                "diagnostic_plugins": [diag_plugin_config_entry],
                "recovery_plugins": [],
            }
        }

        diagnosed_issues = diagnoser.run_diagnostics(all_monitor_data)

        self.assertEqual(len(diagnosed_issues), 1)
        error_issue = diagnosed_issues[0]
        self.assertEqual(error_issue["issue_type"], "DIAGNOSTIC_ERROR")
        self.assertEqual(error_issue["severity"], "error")
        self.assertIn(
            "Exception in plugin CrashingDiagnoser: Diagnoser Died",
            error_issue["details"],
        )
        self.assertEqual(error_issue["target_id"], target_id)
        self.assertEqual(error_issue["diagnosed_by"], "CrashingDiagnoser")

    def test_run_diagnostics_no_diagnostic_plugins_for_target(self):
        diagnoser = IssueDiagnoser()
        diagnoser.diagnostic_plugins = {}  # No plugins loaded at all

        target_id = "lonely_target"
        all_monitor_data = {target_id: [{"target_id": target_id, "data": "some data"}]}

        # Target is configured, but has no diagnostic_plugins list or it's empty
        SUT_config.MONITORED_TARGETS = {
            target_id: {
                "enabled": True,
                "plugin": "AnyMonitor",
                "config": {},
                "diagnostic_plugins": [],  # Empty list
                "recovery_plugins": [],
            }
        }
        diagnosed_issues = diagnoser.run_diagnostics(all_monitor_data)
        self.assertEqual(diagnosed_issues, [])

        # Test with diagnostic_plugins key missing entirely
        SUT_config.MONITORED_TARGETS = {
            target_id: {
                "enabled": True,
                "plugin": "AnyMonitor",
                "config": {},
                # "diagnostic_plugins" key is missing
                "recovery_plugins": [],
            }
        }
        diagnosed_issues = diagnoser.run_diagnostics(all_monitor_data)
        self.assertEqual(diagnosed_issues, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
