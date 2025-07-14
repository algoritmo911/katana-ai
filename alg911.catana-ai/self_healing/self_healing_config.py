import os

# self_healing_config.py
# Centralized configuration for the Self-Healing Module

# --- General Settings ---
MODULE_ENABLED = True  # Master switch for the entire self-healing module
MAIN_LOOP_INTERVAL_SECONDS = 60  # How often the orchestrator runs its cycle
MAX_CONSECUTIVE_RECOVERY_ATTEMPTS = (
    3  # Max recovery attempts for a single issue before escalating/logging critical
)
LOG_LEVEL = "INFO"  # Default logging level for the module (DEBUG, INFO, WARNING, ERROR, CRITICAL)

# --- Paths ---
# Assuming this config file is in alg911.catana-ai/self_healing/
# BASE_DIR for the module is alg911.catana-ai/self_healing/
MODULE_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# PROJECT_BASE_DIR for the entire Katana project (alg911.catana-ai)
PROJECT_BASE_DIR = os.path.dirname(MODULE_BASE_DIR)

# --- Monitoring Defaults ---
DEFAULT_HTTP_TIMEOUT_SECONDS = 10
DEFAULT_PROCESS_CHECK_INTERVAL_SECONDS = 30

# --- Monitored Services/Components Configuration ---
# This section defines what to monitor and how.
# Each entry key is a unique identifier for the monitored target.
# 'plugin': Name of the MonitoringPlugin to use.
# 'config': Plugin-specific configuration.
# 'diagnostics': List of DiagnosticPlugins to run on this monitor's output.
# 'recoveries': List of RecoveryPlugins to consider if an issue is diagnosed.

MONITORED_TARGETS = {
    "katana_api": {
        "enabled": True,
        "plugin": "HttpAvailabilityMonitor",  # To be implemented in basic_plugins.py
        "config": {
            "url": "http://localhost:5001/api/v1/health",  # Example API health endpoint
            "method": "GET",
            "expected_status_code": 200,
            "timeout_seconds": 5,
        },
        "diagnostic_plugins": [
            {
                "plugin": "HttpStatusIssueDiagnoser",  # To be implemented
                "config": {"critical_status_codes": [500, 502, 503, 504]},
            }
        ],
        "recovery_plugins": [
            {
                "plugin": "ServiceRestartRecovery",  # To be implemented
                "config": {
                    "service_name": "katana_api_service_name_in_systemd_or_script"
                },  # Placeholder
            }
        ],
    },
    "katana_main_process": {
        "enabled": True,
        "plugin": "ProcessRunningMonitor",  # To be implemented
        "config": {
            "process_name_pattern": "katana_agent.py",  # Example: match by script name
            # "pid_file": "/var/run/katana_agent.pid", # Alternative: monitor by PID file
        },
        "diagnostic_plugins": [
            {"plugin": "ProcessNotRunningDiagnoser", "config": {}}  # To be implemented
        ],
        "recovery_plugins": [
            {
                "plugin": "ServiceRestartRecovery",
                "config": {"service_name": "katana_agent_service_name"},  # Placeholder
            }
        ],
    },
    "katana_events_log": {
        "enabled": True,
        "plugin": "LogFileMonitor",  # To be implemented
        "config": {
            "log_file_path": os.path.join(PROJECT_BASE_DIR, "katana_events.log"),
            "error_patterns": [
                r"CRITICAL",
                r"Error decoding JSON",
                r"Failed to save",
                # Add more critical patterns specific to katana_events.log
            ],
        },
        "diagnostic_plugins": [
            {
                "plugin": "LogPatternDiagnoser",  # To be implemented
                "config": {
                    "critical_pattern_threshold": 1
                },  # Trigger if 1 or more critical patterns found
            }
        ],
        "recovery_plugins": [
            # Example: Maybe no direct recovery, but could trigger a notification
            # {
            #     "plugin": "NotificationRecovery", # Example, not in current plan
            #     "config": {"message": "Critical errors found in katana_events.log"}
            # }
        ],
    },
    # Add more services like UI, backend components, databases etc.
}


# --- Plugin Specific Configurations (if not covered in MONITORED_TARGETS) ---
# Example:
# PLUGIN_CONFIG_ServiceRestartRecovery = {
#     "default_restart_command_template": "sudo systemctl restart {service_name}",
#     "service_specific_commands": {
#         "katana_api_service": "/opt/katana/bin/restart_api.sh",
#     }
# }


# --- Helper function to get a specific target's config ---
def get_target_config(target_id: str):
    return MONITORED_TARGETS.get(target_id)


if __name__ == "__main__":
    print("Self-Healing Module Configuration:")
    print(f"  Module Enabled: {MODULE_ENABLED}")
    print(f"  Main Loop Interval: {MAIN_LOOP_INTERVAL_SECONDS} seconds")
    print(f"  Project Base Dir: {PROJECT_BASE_DIR}")
    print(f"  Module Base Dir: {MODULE_BASE_DIR}")

    print("\nMonitored Targets:")
    for target_id, config in MONITORED_TARGETS.items():
        print(f"  Target ID: {target_id}")
        print(f"    Enabled: {config.get('enabled')}")
        print(f"    Monitor Plugin: {config.get('plugin')}")
        print(f"    Monitor Config: {config.get('config')}")
        print(f"    Diagnostic Plugins: {len(config.get('diagnostic_plugins', []))}")
        print(f"    Recovery Plugins: {len(config.get('recovery_plugins', []))}")

    api_config = get_target_config("katana_api")
    if api_config:
        print(f"\nExample: Config for 'katana_api' URL: {api_config['config']['url']}")

    print(f"\nConfiguration loaded from: {__file__}")
