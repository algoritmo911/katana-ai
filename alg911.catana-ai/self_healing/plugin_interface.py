from abc import ABC, abstractmethod
from typing import Any, Dict, List

class MonitoringPlugin(ABC):
    """
    Abstract Base Class for all monitoring plugins.
    Monitoring plugins are responsible for collecting health data about a specific service or component.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Returns the unique name of the plugin."""
        pass

    @abstractmethod
    def check_health(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs the health check.

        Args:
            config: A dictionary containing configuration specific to this plugin instance
                    (e.g., URL to check, process name, log file path).

        Returns:
            A dictionary containing the health data collected.
            The structure can vary but should be consistent for a given plugin.
            Example: {"status": "ok", "details": "Service running normally"}
                     {"status": "error", "error_message": "Connection refused", "response_time_ms": 0}
        """
        pass


class DiagnosticPlugin(ABC):
    """
    Abstract Base Class for all diagnostic plugins.
    Diagnostic plugins analyze data (often from monitoring plugins) to identify specific issues.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Returns the unique name of the plugin."""
        pass

    @abstractmethod
    def diagnose(self, monitor_data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyzes monitoring data to diagnose issues.

        Args:
            monitor_data: A list of data points, typically the output from one or more MonitoringPlugins.
            config: A dictionary containing configuration specific to this plugin instance
                    (e.g., error patterns to look for, thresholds).

        Returns:
            A list of diagnosed issues. Each issue should be a dictionary.
            Example: [{"issue_type": "API_UNREACHABLE", "severity": "critical", "details": "API at http://localhost:8000 not responding"}]
                     [{"issue_type": "HIGH_CPU_USAGE", "severity": "warning", "component": "payment_service", "value": "95%"}]
        """
        pass


class RecoveryPlugin(ABC):
    """
    Abstract Base Class for all recovery plugins.
    Recovery plugins execute actions to attempt to fix diagnosed issues.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Returns the unique name of the plugin."""
        pass

    @abstractmethod
    def can_recover(self, issue: Dict[str, Any]) -> bool:
        """
        Checks if this plugin can attempt to recover from the given issue.

        Args:
            issue: A dictionary describing the diagnosed issue (output from a DiagnosticPlugin).

        Returns:
            True if the plugin can handle this type of issue, False otherwise.
        """
        pass

    @abstractmethod
    def attempt_recovery(self, issue: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempts to perform a recovery action for the given issue.

        Args:
            issue: A dictionary describing the diagnosed issue.
            config: A dictionary containing configuration specific to this plugin instance
                    (e.g., service name to restart, script path to execute).

        Returns:
            A dictionary describing the outcome of the recovery attempt.
            Example: {"status": "success", "action_taken": "Restarted payment_service", "details": "Service restarted successfully."}
                     {"status": "failed", "action_taken": "Restart payment_service", "error_message": "Failed to restart service: command not found."}
        """
        pass

if __name__ == "__main__":
    # This section is for basic demonstration or direct testing of the interfaces.
    # It won't be executed when the module is imported.

    class MyHttpMonitor(MonitoringPlugin):
        def get_name(self) -> str:
            return "MyHttpMonitor"
        def check_health(self, config: Dict[str, Any]) -> Dict[str, Any]:
            print(f"MyHttpMonitor checking health with config: {config}")
            # Simulate a health check
            if config.get("url") == "http://good.service":
                return {"status": "ok", "response_time_ms": 50}
            else:
                return {"status": "error", "error_message": "Service unavailable", "url": config.get("url")}

    class MyIssueClassifier(DiagnosticPlugin):
        def get_name(self) -> str:
            return "MyIssueClassifier"
        def diagnose(self, monitor_data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
            print(f"MyIssueClassifier diagnosing with config: {config}")
            issues = []
            for data_point in monitor_data:
                if data_point.get("status") == "error" and "unavailable" in data_point.get("error_message", ""):
                    issues.append({
                        "issue_type": "SERVICE_UNAVAILABLE",
                        "severity": "critical",
                        "details": data_point.get("error_message"),
                        "source_monitor": data_point.get("monitor_name", "UnknownMonitor"),
                        "target": data_point.get("url")
                    })
            return issues

    class MyServiceRestarter(RecoveryPlugin):
        def get_name(self) -> str:
            return "MyServiceRestarter"
        def can_recover(self, issue: Dict[str, Any]) -> bool:
            return issue.get("issue_type") == "SERVICE_UNAVAILABLE"

        def attempt_recovery(self, issue: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
            print(f"MyServiceRestarter attempting recovery for issue: {issue} with config: {config}")
            service_name_to_restart = issue.get("target") # Simplistic mapping
            if service_name_to_restart:
                # Simulate restarting
                print(f"Simulating restart of service: {service_name_to_restart}")
                return {"status": "success", "action_taken": f"Restarted {service_name_to_restart}"}
            else:
                return {"status": "failed", "action_taken": "Restart attempt", "error_message": "Could not determine service to restart"}

    # Example usage
    http_monitor = MyHttpMonitor()
    bad_service_health = http_monitor.check_health({"url": "http://bad.service", "monitor_name": http_monitor.get_name()})
    good_service_health = http_monitor.check_health({"url": "http://good.service", "monitor_name": http_monitor.get_name()})

    print("\nMonitor Outputs:")
    print(f"Bad service: {bad_service_health}")
    print(f"Good service: {good_service_health}")

    diagnoser = MyIssueClassifier()
    diagnosed_issues = diagnoser.diagnose(
        [bad_service_health, good_service_health],
        {"error_patterns": ["unavailable"]}
    )

    print("\nDiagnosed Issues:")
    for issue in diagnosed_issues:
        print(issue)

    restarter = MyServiceRestarter()
    print("\nRecovery Attempts:")
    for issue in diagnosed_issues:
        if restarter.can_recover(issue):
            recovery_result = restarter.attempt_recovery(issue, {"restart_command_template": "systemctl restart {}"})
            print(f"Recovery for {issue.get('target')}: {recovery_result}")
        else:
            print(f"Cannot recover issue: {issue.get('issue_type')} for {issue.get('target')} with {restarter.get_name()}")

    print(f"\nPlugin interface defined in: {__file__}")
