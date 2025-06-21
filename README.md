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
    pytest
    ```
    Alternatively, you can be more specific:
    ```bash
    python -m pytest test_bot.py
    ```
    The project uses `pytest` as the standard framework for unit testing. Ensure all tests pass before committing changes.

## Testing with Coverage

To ensure code quality and identify untested parts of the codebase, you can run the unit tests with coverage analysis using `pytest` and `pytest-cov`.

1.  **Install Dependencies**:
    If you don't have them installed, get them via pip:
    ```bash
    pip install pytest pytest-cov
    ```

2.  **Run Tests with Coverage**:
    Navigate to the bot's root directory in your terminal and run the following command:
    ```bash
    python -m pytest --cov=. test_bot.py
    ```
    Alternatively, you can often just run:
    ```bash
    pytest --cov=.
    ```
    (Assuming `test_bot.py` is discoverable by `pytest`).

3.  **View Coverage Report**:
    `pytest-cov` will typically output a summary report to the console automatically, including missing line numbers if configured (e.g., via `--cov-report=term-missing` which is used in `run_checks.sh`).

    For a more detailed HTML report that you can view in your browser (this is often the most useful report):
    ```bash
    python -m pytest --cov=. --cov-report=html test_bot.py
    ```
    This will create an `htmlcov/` directory (usually). Open `htmlcov/index.html` in a web browser to explore the coverage results interactively. The `run_checks.sh` script also generates this report.

#### Analyzing the Coverage Report

The HTML report generated by `pytest-cov` (located in the `htmlcov/` directory, open `index.html`) is particularly useful for detailed analysis:

*   **Overview**: The main page shows a summary table with coverage percentages for each file.
*   **File Details**: Clicking on a filename takes you to a view of the source code, annotated line by line:
    *   **Green lines** are covered by tests.
    *   **Red lines** are not covered.
    *   **Yellow lines** (if applicable, for branch coverage) indicate branches that were not taken (e.g., an `if` condition that was never false during tests).
*   **Metrics**:
    *   **Stmts (Statements)**: Total number of executable statements.
    *   **Miss**: Number of statements not executed.
    *   **Cover**: Coverage percentage (`(Stmts - Miss) / Stmts * 100`).
    *   **Branch** (if available and configured): Number of possible execution branches.
    *   **BrPart (Branch Partial)**: Number of branches not fully tested.

#### Tips for Improving Coverage

*   **Focus on Red Lines**: Prioritize writing tests for lines marked in red. These represent completely untested code.
*   **Address Yellow Lines (Branch Coverage)**: If you see yellow lines, it means some conditions in your code (e.g., `if/else`, `while` loops, exception handling) haven't been fully explored. Write tests that trigger these different paths. For example, if an `if condition:` is always true in your tests, add a test where it's false.
*   **Test Edge Cases**: Ensure your tests cover not just typical scenarios but also edge cases, invalid inputs, and potential error conditions. This often reveals untested code paths.
*   **Complex Logic**: Pay special attention to functions or modules with complex logic. These are more likely to have hidden untested paths.
*   **Iterative Improvement**: Don't aim for 100% coverage immediately if it's a large legacy codebase. Incrementally add tests to critical and new functionalities, and gradually improve coverage over time. Aim for high coverage on new or modified code.
*   **Exclude Non-Critical Code**: `pytest-cov` (like `coverage.py`) can be configured to exclude non-critical code from the report (e.g., boilerplate, test helper files themselves, or parts of the code that are not feasible to test). This helps focus the report on relevant application code. You can do this via a `.coveragerc` file or command-line options for `pytest`.

By regularly running tests with coverage and analyzing the report, you can systematically improve the quality and reliability of the bot.

## Automated Checks Script

A script `run_checks.sh` is provided to automate common quality checks, including running tests with coverage and linting the codebase.

### Prerequisites

Before running the script, ensure you have the necessary tools installed. If you haven't already, you can install them via pip:

```bash
pip install pytest pytest-cov isort flake8 black
```
(Note: `pyTelegramBotAPI` is also required for the bot itself, as mentioned in the Setup section).

### Running the Script

1.  **Make it executable (if you haven't already or if you pulled it fresh):**
    ```bash
    chmod +x run_checks.sh
    ```
2.  **Execute the script from the root directory of the project:**
    ```bash
    ./run_checks.sh
    ```

The script will perform the following checks:
1.  **Tests and Coverage**: Runs unit tests using `pytest` with `pytest-cov` for coverage analysis. It will display a coverage report (including missing lines) and fail if coverage is below 80% (this threshold can be adjusted in the script).
2.  **Import Sorting**: Checks if Python imports are correctly sorted using `isort`.
3.  **Linting**: Analyzes the code for style and errors using `flake8`.
4.  **Code Formatting**: Checks if the code adheres to `black` formatting standards.

If any step fails, the script will exit immediately, and you will see an error message indicating the problematic check. Address the reported issues and re-run the script until all checks pass.