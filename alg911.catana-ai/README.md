# Katana AI Agent - Project Directory

This directory contains the core files and modules for the Katana AI Agent.
Katana is a multi-purpose agent designed for task management, automation, and interaction, with a focus on future expansions into psychoanalysis, neuro-simulation, and more complex operational logic.

## Overview

The Katana Agent (`katana_agent.py`) is a Python-based application that provides:
- A **Command Line Interface (CLI)** for direct interaction and control.
- **Task processing capabilities** via a JSON-based task queue.
- **Integration with Telegram** for receiving commands and (soon) sending responses.
- A structured logging system for events and debugging.
- A persistent memory store for agent state.

## `katana_agent.py` Details

The core of the agent is the `KatanaCLI` class within `katana_agent.py`.

-   **`KatanaCLI` Class:** Encapsulates all functionalities of the agent, including file I/O, command parsing, command execution, task management, and state persistence.
-   **Main Loop:** When executed, `katana_agent.py` starts an interactive shell. In each iteration of this loop:
    1.  It processes one pending task from the task queue (`katana.commands.json`).
    2.  It then presents a CLI prompt (`katana> `) for user input.
-   **Task Processing:** Tasks are dictionaries read from `katana.commands.json`. Each task has an `action` and `parameters`. The agent updates the task's `status` (e.g., "pending", "processing", "completed", "failed") and stores results.

### Key Data Files:

-   **`katana_memory.json`**: Stores the agent's persistent memory as a JSON object. This includes:
    -   `katana_service_status`: Current status of the Katana service ("running", "stopped", "unknown").
    -   `katana_service_last_start_time`: ISO timestamp of the last service start.
    -   `katana_service_last_stop_time`: ISO timestamp of the last service stop.
    -   Other arbitrary data the agent might need to persist.
-   **`katana.commands.json`**: Acts as the **task queue**. It's a JSON list where each item is a task dictionary. Tasks are added by external triggers (like Telegram webhooks via `n8n_webhook_handler.sh`) or internal CLI commands (like `addtask`).
-   **`katana.history.json`**: Stores a history of commands entered into the CLI.
-   **`katana_events.log`**: A plain text log file for general event logging, agent actions, and debugging information.
-   **`sync_status.json`**: (Related to cloud sync) Stores information about the last synchronization status with a cloud provider.

## CLI Usage

To run the Katana Agent CLI:
```bash
python alg911.catana-ai/katana_agent.py
```

Once the CLI is running, the following commands are available:

-   **`echo <args...>`**: Prints the provided arguments back to the console.
    -   Example: `katana> echo Hello World`
-   **`memdump`**: Prints the current content of `self.agent_memory_state` (from `katana_memory.json`) to the console.
-   **`addtask <action_name> [param_key=param_value ...]`**: Adds a new task to the `katana.commands.json` queue.
    -   Example: `katana> addtask process_telegram_message text="/status" chat_id="12345"`
-   **`start_katana`**: Updates the agent's status to "running" in `katana_memory.json` and records the start time.
-   **`stop_katana`**: Updates the agent's status to "stopped" in `katana_memory.json` and records the stop time.
-   **`status_katana`**: Displays the current service status, last start time, and last stop time from `katana_memory.json`.
-   **`exit`**: Terminates the Katana Agent CLI.

## Task Queue

-   Tasks are stored as JSON objects in the `katana.commands.json` file.
-   They can be added via the `addtask` CLI command or by external systems like the `n8n_webhook_handler.sh` script (which processes incoming Telegram messages).
-   The agent processes one pending task from the queue during each cycle of its main loop.
-   **Task Structure Example (in `katana.commands.json`):**
    ```json
    {
        "command_id": "cmd_uuid_example",
        "action": "process_telegram_message",
        "parameters": {
            "user_id": "telegram_user_123",
            "chat_id": "chat_id_789",
            "text": "/status",
            "original_command_id": "original_n8n_cmd_id"
        },
        "status": "pending", // or processing, completed, failed
        "created_at": "2024-01-01T12:00:00Z",
        "processed_at": null, // or ISO timestamp
        "result": null, // or string describing outcome
        "origin": "telegram_webhook" // or cli_addtask, internal etc.
    }
    ```

## Telegram Integration

-   Incoming messages from Telegram are received by an n8n webhook, which then calls `n8n_webhook_handler.sh`.
-   This script standardizes the Telegram message into a task and adds it to `katana.commands.json` with the action `process_telegram_message`.
-   The Katana Agent processes these tasks, allowing interaction via Telegram.
-   **Implemented Telegram Commands (sent to the bot):**
    -   `/status`: Gets the agent's operational status, service status, and pending task count.
    -   `/echo_tg <message>`: The agent will echo `<message>` back.
    -   `/start_katana`: Starts the Katana service (updates status in `katana_memory.json`).
    -   `/stop_katana`: Stops the Katana service (updates status in `katana_memory.json`).
-   **Configuration for Responses:** To enable the agent to send responses back to Telegram, the `N8N_TELEGRAM_SEND_WEBHOOK_URL` constant at the top of `katana_agent.py` must be configured with your actual n8n webhook URL designed for sending messages.

## Logging

-   The agent uses Python's `logging` module.
-   A logger named `katana_logger` is configured with two handlers:
    -   **Console (StreamHandler):** Outputs messages at `INFO` level and above. Format: `[%(asctime)s] [%(levelname)s] [KatanaAgent] %(message)s`
    -   **File (FileHandler):** Outputs messages at `DEBUG` level and above to `katana_events.log`. Format: `[%(asctime)s] [%(levelname)s] [%(name)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s`

## Unit Tests

-   Unit tests are implemented using Python's `unittest` framework.
-   The main test suite is located in `alg911.catana-ai/test_katana_cli.py`.
-   **Coverage:** The tests cover functionalities such as:
    -   CLI command execution (`echo`, `memdump`, `exit`, service status commands).
    -   Task management (add, get, update tasks).
    -   Processing of tasks from simulated Telegram commands (`/status`, `/echo_tg`, `/start_katana`, `/stop_katana`).
    -   File initialization and history management.
    -   Mocking is used for external dependencies (like `send_telegram_message`) and to control variables like timestamps.
-   Tests operate on temporary files to avoid interfering with actual agent data.

## Configuration

-   **`N8N_TELEGRAM_SEND_WEBHOOK_URL`**: (Required for Telegram responses) This constant is at the top of `katana_agent.py`. It needs to be set to the n8n webhook URL that forwards messages to Telegram.
-   **`rclone.conf`**: (For cloud synchronization) This file needs to be configured if you plan to use `sync_to_cloud.sh`.

## Project Vision (Legacy Context)

Katana was initially envisioned with a broader scope including psychoanalysis, routine automation, neuro-simulation, and civilizational design through Sapiens Coin. While the current implementation focuses on foundational agent capabilities (CLI, tasking, basic integrations), this broader vision may inform future development.

### Modules (Scaffolded - Legacy)

The following modules were part of the initial project scaffold and represent potential future development areas:
- **`neuro_refueling/`**: For "Нейро-Дозаправка" (Neuro-Refueling).
- **`mind_clearing/`**: For "Модуль Очистки Сознания" (Mind Clearing).

These are currently placeholders and not integrated into the active agent logic.
```
