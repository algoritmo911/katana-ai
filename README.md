# Katana Telegram Bot

The Katana Telegram Bot is designed to process commands sent via Telegram messages in JSON format. It features command validation, logging, and a modular approach to handling different command types.

## Command Format

Commands must be sent as a JSON string in a Telegram message. The JSON object must adhere to the following structure:

```json
{
  "type": "command_name",
  "module": "module_identifier",
  "args": {
    "arg1": "value1",
    "arg2": "value2"
    // ... other arguments
  },
  "id": "unique_command_id"
}
```

### Field Descriptions:

*   **`type`** (String): Specifies the type of command to be executed.
    *   Example: `"log_event"`, `"mind_clearing"`
*   **`module`** (String): **Required.** Indicates the module or category this command pertains to. This field is mandatory for all commands.
    *   Example: `"user_activity"`, `"system_health"`, `"telegram_general"`
*   **`args`** (Object): A JSON object containing arguments specific to the command type.
    *   Example: `{"message": "User logged in"}` for a `log_event`
*   **`id`** (String or Integer): A unique identifier for the command instance.
    *   Example: `"cmd_12345"`, `1678886400`

### Example Commands:

**1. Logging an Event:**

```json
{
  "type": "log_event",
  "module": "user_auth",
  "args": {
    "event_type": "login_success",
    "username": "john_doe"
  },
  "id": "evt_user_login_001"
}
```

**2. Generic Command (saved to file by default):**

```json
{
  "type": "custom_task",
  "module": "data_processing",
  "args": {
    "input_file": "/path/to/input.csv",
    "output_format": "json"
  },
  "id": "task_dp_002"
}
```

## Logging

The bot performs comprehensive logging for monitoring and debugging purposes.

*   **Console Logs**: Real-time logs are printed to the console where the bot is running. These provide immediate feedback on bot operations.
    *   Format: `[LEVEL] Message`
*   **File Logs**: All log messages are also saved to a file named `katana_bot.log` in the same directory where the bot is running.
    *   Format: `YYYY-MM-DD HH:MM:SS,milliseconds - LEVEL - Message`

### Interpreting Logs:

*   **`INFO` Level**: Indicates normal operations, such as:
    *   Bot starting/stopping.
    *   Receiving a new message.
    *   Successfully validating and processing a command.
    *   Saving a command to a file.
*   **`ERROR` Level**: Indicates a problem or failure, such as:
    *   Invalid JSON format in an incoming message.
    *   Missing required fields in a command (e.g., `module`).
    *   Incorrect data type for a command field.
    *   Errors during file operations (e.g., saving a command).
    *   Failures within command-specific handlers.

Each log message includes:
*   A timestamp.
*   The severity level (`INFO` or `ERROR`).
*   For message-related logs: The `chat_id` (user ID) of the sender.
*   The received command text (especially for errors) or relevant command details.

Example Error Log:
`2023-10-27 10:30:00,123 - ERROR - Validation failed for 123456789: Error: Missing required field 'module'. (Command: {"type": "log_event", "args": {}, "id": "xyz"})`

This log indicates that user `123456789` sent a command that was missing the `module` field.

## Setup and Running

1.  **API Token**:
    *   Open `bot.py`.
    *   Replace `'YOUR_API_TOKEN'` with your actual Telegram Bot API token.
    *   ```python
        API_TOKEN = 'YOUR_ACTUAL_TELEGRAM_BOT_API_TOKEN'
        ```
2.  **Dependencies**:
    *   The bot requires the `pyTelegramBotAPI` library. Install it if you haven't already:
        ```bash
        pip install pyTelegramBotAPI
        ```
3.  **Running the Bot**:
    *   Navigate to the bot's directory in your terminal.
    *   Run the bot script:
        ```bash
        python bot.py
        ```

The bot will start, and you should see log messages in the console and in `katana_bot.log`.

## Development

*   **Branch**: All development for these improvements should be done in the `feature/command-handling-enhancements` branch (or similar, based on original issue's "улучшения в управлении коммандами/подвигами").
*   **Testing**: Unit tests are located in `test_bot.py`. Run tests using:
    ```bash
    python -m unittest test_bot.py
    ```
    Ensure all tests pass before committing changes.