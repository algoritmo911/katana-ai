import unittest
from unittest.mock import patch, MagicMock, call
import time

import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from self_healing.orchestrator import SelfHealingOrchestrator
# Need to mock the actual classes used by Orchestrator if not using dependency injection for them
# from self_healing.monitor import ServiceMonitor -> replaced by mock
# from self_healing.diagnostics import IssueDiagnoser -> replaced by mock
# from self_healing.recovery import RecoveryManager -> replaced by mock
from self_healing import self_healing_config as SUT_config
from self_healing.self_healing_logger import logger

logger.setLevel("CRITICAL") # Keep test output clean


class TestSelfHealingOrchestrator(unittest.TestCase):

    def setUp(self):
        # Store original values to restore
        self.original_module_enabled = SUT_config.MODULE_ENABLED
        self.original_loop_interval = SUT_config.MAIN_LOOP_INTERVAL_SECONDS
        self.original_max_attempts = SUT_config.MAX_CONSECUTIVE_RECOVERY_ATTEMPTS
        self.original_monitored_targets = SUT_config.MONITORED_TARGETS

        # Configure for tests
        SUT_config.MODULE_ENABLED = True
        SUT_config.MAIN_LOOP_INTERVAL_SECONDS = 1 # Fast loop for testing
        SUT_config.MAX_CONSECUTIVE_RECOVERY_ATTEMPTS = 2
        SUT_config.MONITORED_TARGETS = {} # Start with empty, specific tests will populate

        # Mock the internal components (Monitor, Diagnoser, RecoveryManager)
        # Patching the __init__ of these is one way, or patching where Orchestrator imports them.
        # Patching 'self_healing.orchestrator.ServiceMonitor' etc.
        self.patch_monitor = patch('self_healing.orchestrator.ServiceMonitor', MagicMock())
        self.patch_diagnoser = patch('self_healing.orchestrator.IssueDiagnoser', MagicMock())
        self.patch_recovery_manager = patch('self_healing.orchestrator.RecoveryManager', MagicMock())

        self.mock_monitor_class = self.patch_monitor.start()
        self.mock_diagnoser_class = self.patch_diagnoser.start()
        self.mock_recovery_manager_class = self.patch_recovery_manager.start()

        # Instances that the orchestrator will create and use
        self.mock_monitor_instance = self.mock_monitor_class.return_value
        self.mock_diagnoser_instance = self.mock_diagnoser_class.return_value
        self.mock_recovery_manager_instance = self.mock_recovery_manager_class.return_value


    def tearDown(self):
        SUT_config.MODULE_ENABLED = self.original_module_enabled
        SUT_config.MAIN_LOOP_INTERVAL_SECONDS = self.original_loop_interval
        SUT_config.MAX_CONSECUTIVE_RECOVERY_ATTEMPTS = self.original_max_attempts
        SUT_config.MONITORED_TARGETS = self.original_monitored_targets

        self.patch_monitor.stop()
        self.patch_diagnoser.stop()
        self.patch_recovery_manager.stop()

    def test_orchestrator_initialization_disabled(self):
        SUT_config.MODULE_ENABLED = False
        orchestrator = SelfHealingOrchestrator()
        self.assertFalse(orchestrator.is_enabled)
        # Ensure internal components were not initialized if module is disabled
        self.mock_monitor_class.assert_not_called()
        self.mock_diagnoser_class.assert_not_called()
        self.mock_recovery_manager_class.assert_not_called()


    def test_orchestrator_initialization_enabled(self):
        SUT_config.MODULE_ENABLED = True
        orchestrator = SelfHealingOrchestrator()
        self.assertTrue(orchestrator.is_enabled)
        self.mock_monitor_class.assert_called_once()
        self.mock_diagnoser_class.assert_called_once()
        self.mock_recovery_manager_class.assert_called_once()
        self.assertEqual(orchestrator.loop_interval_seconds, SUT_config.MAIN_LOOP_INTERVAL_SECONDS)

    def test_run_cycle_no_issues_found(self):
        self.mock_monitor_instance.run_all_checks.return_value = {"target1": [{"status": "ok"}]}
        self.mock_diagnoser_instance.run_diagnostics.return_value = [] # No issues diagnosed

        orchestrator = SelfHealingOrchestrator()
        orchestrator.run_cycle()

        self.mock_monitor_instance.run_all_checks.assert_called_once()
        self.mock_diagnoser_instance.run_diagnostics.assert_called_once_with({"target1": [{"status": "ok"}]})
        self.mock_recovery_manager_instance.attempt_all_recoveries.assert_not_called()
        self.assertEqual(len(orchestrator.active_issues_state), 0)


    def test_run_cycle_issue_found_and_recovered(self):
        monitor_output = {"server_db": [{"status": "error", "details": "DB Connection Lost"}]}
        diagnosed_issue = [{"target_id": "server_db", "issue_type": "DB_DOWN", "severity": "critical", "details": "DB Connection Lost"}]
        recovery_result = [{"status": "success", "action_taken": "Restarted DB", "target_id": "server_db", "issue_type": "DB_DOWN"}]

        self.mock_monitor_instance.run_all_checks.return_value = monitor_output
        self.mock_diagnoser_instance.run_diagnostics.return_value = diagnosed_issue
        self.mock_recovery_manager_instance.attempt_all_recoveries.return_value = recovery_result

        SUT_config.MONITORED_TARGETS = { # Need this for cleanup logic
            "server_db": {"enabled": True, "plugin": "Any", "config": {}}
        }

        orchestrator = SelfHealingOrchestrator()
        orchestrator.run_cycle()

        self.mock_monitor_instance.run_all_checks.assert_called_once()
        self.mock_diagnoser_instance.run_diagnostics.assert_called_once_with(monitor_output)
        self.mock_recovery_manager_instance.attempt_all_recoveries.assert_called_once_with(diagnosed_issue)

        issue_key = orchestrator._generate_issue_key(diagnosed_issue[0])
        self.assertIn(issue_key, orchestrator.active_issues_state)
        self.assertEqual(orchestrator.active_issues_state[issue_key]["recovery_attempts_count"], 1)

        # Simulate next cycle where issue is resolved
        self.mock_monitor_instance.run_all_checks.return_value = {"server_db": [{"status": "ok"}]} # DB is now OK
        self.mock_diagnoser_instance.run_diagnostics.return_value = [] # No issues diagnosed

        orchestrator.run_cycle()
        # Check if the issue was cleared from active_issues_state by _cleanup_resolved_issues
        # This depends on the cleanup logic correctly identifying the resolution.
        # The current _cleanup_resolved_issues is simplistic, relies on target_id being "OK".
        self.assertNotIn(issue_key, orchestrator.active_issues_state)


    def test_run_cycle_issue_max_recovery_attempts_reached(self):
        SUT_config.MAX_CONSECUTIVE_RECOVERY_ATTEMPTS = 1 # Set low for this test
        monitor_output = {"web_server": [{"status": "error", "details": "503 Service Unavailable"}]}
        diagnosed_issue = [{"target_id": "web_server", "issue_type": "HTTP_503", "severity": "critical"}]
        failed_recovery_result = [{"status": "failed", "action_taken": "Restart failed", "target_id": "web_server", "issue_type": "HTTP_503"}]

        self.mock_monitor_instance.run_all_checks.return_value = monitor_output
        self.mock_diagnoser_instance.run_diagnostics.return_value = diagnosed_issue
        self.mock_recovery_manager_instance.attempt_all_recoveries.return_value = failed_recovery_result

        orchestrator = SelfHealingOrchestrator()

        # Cycle 1: Attempt recovery
        orchestrator.run_cycle()
        self.mock_recovery_manager_instance.attempt_all_recoveries.assert_called_once_with(diagnosed_issue)
        issue_key = orchestrator._generate_issue_key(diagnosed_issue[0])
        self.assertEqual(orchestrator.active_issues_state[issue_key]["recovery_attempts_count"], 1)

        # Cycle 2: Issue persists, max attempts (1) reached, should not attempt recovery again
        # Reset mock for attempt_all_recoveries to check it's not called
        self.mock_recovery_manager_instance.attempt_all_recoveries.reset_mock()
        # Diagnoser still reports the issue
        self.mock_diagnoser_instance.run_diagnostics.return_value = diagnosed_issue
        # Monitor still reports error
        self.mock_monitor_instance.run_all_checks.return_value = monitor_output


        orchestrator.run_cycle()
        self.mock_recovery_manager_instance.attempt_all_recoveries.assert_not_called() # Key assertion
        self.assertEqual(orchestrator.active_issues_state[issue_key]["recovery_attempts_count"], 1) # Count should not increment further for recovery

    def test_cleanup_resolved_issues(self):
        orchestrator = SelfHealingOrchestrator()
        issue1 = {"target_id": "service_A", "issue_type": "TIMEOUT", "details": "detail A"}
        issue2 = {"target_id": "service_B", "issue_type": "DISK_FULL", "details": "detail B"}
        key1 = orchestrator._generate_issue_key(issue1)
        key2 = orchestrator._generate_issue_key(issue2)

        current_time = time.time()
        orchestrator.active_issues_state = {
            key1: {"first_detected_ts": current_time - 60, "last_detected_ts": current_time - 30, "recovery_attempts_count": 1, "original_issue_details": issue1},
            key2: {"first_detected_ts": current_time - 60, "last_detected_ts": current_time - 5, "recovery_attempts_count": 0, "original_issue_details": issue2}
        }

        # Simulate current monitor data: service_A is now OK, service_B still has issues (or no data)
        current_monitor_data_showing_A_ok = {
            "service_A": [{"status": "ok", "target_id": "service_A"}],
            # service_B might be missing or still showing errors
            "service_B": [{"status": "error", "target_id": "service_B"}]
        }
        SUT_config.MONITORED_TARGETS = { # Needed for the current _cleanup_resolved_issues logic
            "service_A": {"enabled": True, "plugin": "Any", "config": {}},
            "service_B": {"enabled": True, "plugin": "Any", "config": {}}
        }


        orchestrator._cleanup_resolved_issues(current_monitor_data_showing_A_ok)

        self.assertNotIn(key1, orchestrator.active_issues_state) # service_A's issue should be cleared
        self.assertIn(key2, orchestrator.active_issues_state)   # service_B's issue should remain


    def test_cleanup_stale_issues(self):
        orchestrator = SelfHealingOrchestrator()
        SUT_config.MAIN_LOOP_INTERVAL_SECONDS = 10 # Loop interval
        # Staleness threshold is loop_interval * 5 = 50 seconds

        issue_stale = {"target_id": "stale_service", "issue_type": "STALE_ERROR"}
        key_stale = orchestrator._generate_issue_key(issue_stale)

        current_time = time.time()
        orchestrator.active_issues_state = {
            key_stale: {
                "first_detected_ts": current_time - 100,
                "last_detected_ts": current_time - 60, # Last seen 60s ago, > 50s threshold
                "recovery_attempts_count": 1,
                "original_issue_details": issue_stale
            }
        }
        # Simulate monitor data where 'stale_service' is not reporting anything (neither OK nor error)
        current_monitor_data_empty = {}
        SUT_config.MONITORED_TARGETS = {
             "stale_service": {"enabled": True, "plugin": "Any", "config": {}}
        }

        orchestrator._cleanup_resolved_issues(current_monitor_data_empty)
        self.assertNotIn(key_stale, orchestrator.active_issues_state) # Stale issue should be cleared

    # Test for the start method is harder as it's an infinite loop.
    # Could test it starts a thread if patching `time.sleep` and `threading.Thread`.
    # For now, focusing on run_cycle.

if __name__ == '__main__':
    unittest.main(verbosity=2)
