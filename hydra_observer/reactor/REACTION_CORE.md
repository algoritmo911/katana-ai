# Katana Hydra Reaction Core

The Katana Hydra Reaction Core is a trigger-based system for smart responders. It allows for the registration of reactions to events, and the triggering of those reactions from probes and watchers.

## Available Reactions

### `high_cpu`

-   **Trigger:**  `probes.py` when CPU usage exceeds 90%.
-   **Data:** `{"cpu_percent": <float>}`
-   **Action:** Logs a warning message. In the future, this will send an alert to a monitoring channel.

### `command_flood`

-   **Trigger:** `watchers.py` (placeholder).
-   **Data:** `{}`
-   **Action:** Logs a warning message. In the future, this will throttle command processing.

### `agent_unresponsive`

-   **Trigger:** `watchers.py` (placeholder).
-   **Data:** `{"agent_id": <string>}`
-   **Action:** Logs an error message. In the future, this will attempt to restart the agent.

### `latency_spike`

-   **Trigger:** `watchers.py` (placeholder).
-   **Data:** `{"latency_ms": <int>}`
-   **Action:** Logs a warning message. In the future, this will send a POST request to an external monitoring system.

## Fallback Mechanism

If any reaction handler fails to execute, the `ReactionCore` will call a fallback handler. This handler will log a critical error and, in the future, will send a notification to a dev channel to alert the team of the failure.
