# katana-ai

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