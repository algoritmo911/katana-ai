# Katana Self-Healing Module

## Overview

The Self-Healing Module is a component of the Katana AI Concierge system designed to automatically detect, diagnose, and recover from system failures and operational issues. Its goal is to maintain system stability and availability with minimal human intervention.

The module operates on a cyclical basis:
1.  **Monitor**: Collects health data from various system components and services using configurable monitoring plugins.
2.  **Diagnose**: Analyzes the collected data using diagnostic plugins to identify specific problems or anomalies.
3.  **Recover**: Attempts to resolve diagnosed issues by executing recovery actions through recovery plugins.

This process repeats, allowing the system to adapt to changing conditions and attempt to restore itself to a healthy state.

## Core Components

*   **`orchestrator.py` (SelfHealingOrchestrator)**:
    *   The central coordinator of the module.
    *   Manages the main monitor-diagnose-recover loop.
    *   Tracks active issues, manages recovery attempt limits, and handles issue resolution state.
*   **`monitor.py` (ServiceMonitor)**:
    *   Responsible for running monitoring plugins.
    *   Collects health data based on configurations in `self_healing_config.py`.
*   **`diagnostics.py` (IssueDiagnoser)**:
    *   Runs diagnostic plugins on data provided by the `ServiceMonitor`.
    *   Identifies and reports specific issues.
*   **`recovery.py` (RecoveryManager)**:
    *   Manages and executes recovery plugins based on diagnosed issues.
    *   Selects appropriate recovery actions for given problems.
*   **`plugin_interface.py`**:
    *   Defines the abstract base classes (`MonitoringPlugin`, `DiagnosticPlugin`, `RecoveryPlugin`) that all plugins must implement. This ensures a consistent structure for extending the module's capabilities.
*   **`plugins/` directory**:
    *   Contains concrete implementations of the plugin interfaces.
    *   `basic_plugins.py`: Includes initial plugins for common tasks like HTTP checks, process monitoring, log scanning, and service restarts.
*   **`self_healing_config.py`**:
    *   Central configuration file for the module.
    *   Defines which targets to monitor, which plugins to use for each, plugin-specific parameters, loop intervals, retry limits, etc.
*   **`self_healing_logger.py`**:
    *   Sets up dedicated logging for the self-healing module, typically to `logs/self_healing.log`.
*   **`tests/` directory**:
    *   Contains unit tests for the module's components.

## Plugin Architecture

The module is designed with a plugin architecture to be extensible:

*   **Monitoring Plugins**: Implement `MonitoringPlugin` to add new ways of collecting health data (e.g., checking database connectivity, queue lengths, specific application metrics).
*   **Diagnostic Plugins**: Implement `DiagnosticPlugin` to add new logic for analyzing data and identifying root causes or specific failure modes.
*   **Recovery Plugins**: Implement `RecoveryPlugin` to add new automated actions to fix problems (e.g., clearing caches, scaling resources, failing over to a replica).

Plugins are dynamically loaded and configured via `self_healing_config.py`.

## Configuration

Key aspects of the self-healing module are configured in `alg911.catana-ai/self_healing/self_healing_config.py`:

*   `MODULE_ENABLED`: Master switch for the entire module.
*   `MAIN_LOOP_INTERVAL_SECONDS`: How often the orchestrator runs its full cycle.
*   `MAX_CONSECUTIVE_RECOVERY_ATTEMPTS`: Limits how many times a recovery is attempted for the same persistent issue.
*   `MONITORED_TARGETS`: A dictionary defining each component/service to be monitored, including:
    *   Which monitoring plugin to use and its specific configuration.
    *   Which diagnostic plugins to apply to its data.
    *   Which recovery plugins are available if an issue is found with this target.

## Logging

The module logs its activities to `alg911.catana-ai/logs/self_healing.log`. This includes details about monitoring checks, diagnosed issues, recovery attempts, and errors within the module itself.

## Future Enhancements

*   More sophisticated state management for issues.
*   A wider range of built-in plugins.
*   Integration with external alerting systems.
*   Web UI for viewing module status and history (if Katana develops a UI).
*   More granular control over plugin execution and dependencies.
*   Ability for plugins to contribute to a shared knowledge base about system health.

## Running Tests
Unit tests for this module are located in the `self_healing/tests/` directory. They can be run using a test runner like `pytest` or `python -m unittest discover`. For example, from the `alg911.catana-ai` directory:

```bash
python -m unittest discover -s self_healing/tests -p "test_*.py"
```
or
```bash
pytest self_healing/tests/
```
Ensure that the `requests` library is installed (`pip install requests`), as it is a dependency for `HttpAvailabilityMonitor` plugin.
