# Katana AI

This repository contains the Katana AI monorepo.

## Getting Started: Environment Setup with Poetry

This project uses [Poetry](https://python-poetry.org/) for dependency management and running scripts.

### Prerequisites

Ensure you have Poetry installed. You can find installation instructions [here](https://python-poetry.org/docs/#installation).

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd katana-ai
    ```

2.  **Install dependencies:**
    This command will create a virtual environment inside the project directory and install all necessary main and development dependencies.
    ```bash
    poetry install --with dev
    ```

### Running Tests

To run the entire test suite, use the following command. This will execute `pytest` within the Poetry-managed environment.
```bash
poetry run pytest
```

---

## Logging

This project utilizes Python's standard `logging` module with a centralized configuration (`katana.utils.logging_config`) for consistent logging practices across its components.

### Log Format (JSON)

Application logs are primarily written in JSON format to log files, facilitating structured querying and analysis. Key fields in each JSON log entry include:

*   `timestamp`: ISO 8601 formatted timestamp in UTC (e.g., `2023-10-26T10:30:55.123456+00:00`).
*   `level`: The log level (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
*   `message`: The main log message string.
*   `module`: The name of the Python module where the log originated (e.g., "katana_bot", "katana_mci_agent").
*   `function`: The name of the function within the module where the log call was made.
*   `line_number`: The line number in the source file where the log call was made.
*   `exception`: If an exception was logged (e.g., via `logger.exception()` or `logger.error(exc_info=True)`), this field contains the full exception traceback.
*   **Extra Fields**: Additional contextual information may be included based on the specific log. Common extra fields are:
    *   `user_id`: For `katana_bot.py`, logs related to user interactions.
    *   `command_id`: For `katana_mci_agent.py`, logs related to command processing.
    *   Other custom key-value pairs passed via the `extra` parameter in logging calls.

### Log Examples

Below are conceptual examples of what log entries might look like. Actual timestamps, line numbers, and specific messages will vary.

**Example: INFO Log (Agent Command Processing)**

```json
{
  "timestamp": "2024-07-25T10:30:05.123456+00:00",
  "level": "INFO",
  "message": "Processing command, type: trigger_module, file: cmd_trigger_example_20240725103000123456.json",
  "module": "katana_mci_agent",
  "function": "main",
  "line_number": 350,
  "command_id": "cmd_trigger_example_12345"
}
```

**Example: ERROR Log with Exception (Bot Message Handling)**

```json
{
  "timestamp": "2024-07-25T10:32:15.654321+00:00",
  "level": "ERROR",
  "message": "An unexpected error occurred in handle_message: SimFailedError",
  "module": "katana_bot",
  "function": "handle_message",
  "line_number": 125,
  "user_id": "user_67890",
  "exception": "Traceback (most recent call last):\\n  File \"/app/katana/bot/katana_bot.py\", line 120, in handle_message\\n    result = external_service.call(user_text)\\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \"/app/some_service.py\", line 42, in call\\n    raise SimFailedError(\"Service communication failed\")\\nSimFailedError: Service communication failed"
}
```

### Understanding `extra` Fields

The `extra` parameter in logging calls (e.g., `logger.info("message", extra={"key": "value"})`) is used to add custom key-value pairs to log records. These provide context-specific information relevant to the logged event.

In the JSON log output, these `extra` fields appear as top-level keys alongside the standard logging fields.

**Example: `user_id` in Bot Logs**

When the Telegram bot logs an interaction, it often includes the `user_id`:

```json
{
  "timestamp": "2024-07-25T10:35:00.789012+00:00",
  "level": "INFO",
  "message": "Received /start command",
  "module": "katana_bot",
  "function": "start",
  "line_number": 60,
  "user_id": "user_12345"
}
```

**Example: `command_id` and other details in Agent Logs**

The MCI Agent includes `command_id` and potentially other details related to command execution or errors:

```json
{
  "timestamp": "2024-07-25T10:38:00.987654+00:00",
  "level": "ERROR",
  "message": "Module 'example_module' reported error.",
  "module": "katana_mci_agent",
  "function": "execute_module",
  "line_number": 150,
  "command_id": "cmd_abc_789",
  "error_message": "Required parameter 'x' not found."
}
```

### Log Levels

Standard Python logging levels are used:

*   **DEBUG**: Detailed information, typically of interest only when diagnosing problems. Includes verbose information about operations, states, and data.
*   **INFO**: Confirmation that things are working as expected. Used for significant operational events like startup, shutdown, command processing, or important user interactions.
*   **WARNING**: An indication that something unexpected happened, or indicative of some problem in the near future (e.g., 'disk space low'). The software is still working as expected.
*   **ERROR**: Due to a more serious problem, the software has not been able to perform some function. Typically used when specific operations fail.
*   **CRITICAL**: A serious error, indicating that the program itself may be unable to continue running. Used for critical failures, e.g., inability to start essential services.

### Log File Locations and Rotation

*   **Katana MCI Agent (`katana/mci_agent/katana_agent.py`):**
    *   Log File: `katana/mci_agent/logs/katana_events.log`
*   **Katana Telegram Bot (`katana/bot/katana_bot.py`):**
    *   Log File: `katana/bot/logs/katana_bot.log`

**Log Rotation Policy:**
Log files are configured to rotate when they reach approximately 1MB in size. A maximum of 5 backup files (e.g., `katana_events.log.1`, `katana_events.log.2`, etc.) are kept.

### Console Logs

In addition to JSON file logging, logs are also output to the console (stdout) in a human-readable format. This is primarily for real-time monitoring during development or when running interactively. The console log level also defaults to DEBUG.