# Katana Project

This project consists of a Telegram bot and a React-based user interface.

## Project Structure

-   `/bot`: Contains the Python code for the Telegram bot.
    -   `katana_bot.py`: The main script for the bot.
    -   `commands/`: Directory where the bot stores received commands.
-   `/ui`: Contains the React (Vite + TypeScript) frontend application. This is the primary user interface.
-   `/legacy_ui`: Contains an older or alternative version of the UI. Its specific purpose may need further clarification, but it's not the primary interface.
-   `.gitignore`: Specifies intentionally untracked files that Git should ignore.

## Bot Instructions

The Telegram bot is built with Python and `pyTelegramBotAPI`.

### Prerequisites

-   Python 3.x
-   Dependencies listed in `bot/requirements.txt`

### Environment Variables

Before running the bot, you need to set the following environment variable:

-   `KATANA_TELEGRAM_TOKEN`: Your Telegram Bot API token.
    Example: `export KATANA_TELEGRAM_TOKEN="123456:ABCDEFghijKLMNOpqrsTUVWxyz12345"`

### Running the Bot

1.  Navigate to the bot directory:
    ```bash
    cd bot
    ```
2.  **Recommended: Create and activate a Python virtual environment.** For example:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  Install dependencies (if you haven't already):
    ```bash
    pip install -r requirements.txt
    ```
4.  Run the bot:
    ```bash
    python katana_bot.py
    ```

## UI (React App) Instructions

The main user interface is a React application built with Vite and TypeScript, located in the `/ui` directory.

### Prerequisites

-   Node.js and npm (or yarn)

### Running the UI (Development)

1.  Navigate to the UI directory:
    ```bash
    cd ui
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
    (or `yarn install` if you prefer yarn)
3.  Start the development server:
    ```bash
    npm run dev
    ```
    This will typically open the application in your browser at `http://localhost:5173` (the port might vary).

### Building the UI (Production)

1.  Navigate to the UI directory (if not already there):
    ```bash
    cd ui
    ```
2.  Install dependencies (if you haven't already):
    ```bash
    npm install
    ```
3.  Run the build script:
    ```bash
    npm run build
    ```
    This will create a `dist` folder in the `ui` directory with the production-ready static assets.

## Bot API Endpoints

The Python bot now includes an integrated Flask HTTP server providing API endpoints to interact with the Katana system. This API is used by the Katana Dashboard UI.

**Running the Bot with API Server:**
The `python bot/katana_bot.py` command will automatically start both the Telegram bot polling and the Flask API server. The API server runs on port `5001` by default (e.g., `http://localhost:5001`).

**CORS:**
The API is configured to allow Cross-Origin Resource Sharing (CORS) requests from `http://localhost:5173` (the default Vite development server address for the UI).

**Dependencies:**
The API server uses `Flask` and `Flask-CORS`. These have been added to `bot/requirements.txt`. Ensure you have installed dependencies after pulling changes:
```bash
cd bot
pip install -r requirements.txt
```

### Available Endpoints:

All endpoints are prefixed with `/api`.

1.  **GET `/api/`**
    *   **Description**: Root endpoint to check if the API server is running.
    *   **Response (200 OK)**:
        ```json
        {
          "message": "Katana Bot API is running"
        }
        ```

2.  **GET `/api/status`**
    *   **Description**: Retrieves the current status of the bot and the API server.
    *   **Response (200 OK)**:
        ```json
        {
          "status": "Online", // API server status
          "uptime": "0d 0h 5m 12s", // API server uptime
          "ping": "N/A", // Placeholder
          "bot_status": "Polling (Assumed)", // Simplified Telegram bot status
          "timestamp": "2023-10-27T10:20:30.123Z" // Current server time
        }
        ```
    *   **Error Response (500 Internal Server Error)**:
        ```json
        {
          "success": false,
          "error": "Failed to retrieve status",
          "details": "<error_details>"
        }
        ```

3.  **GET `/api/logs`**
    *   **Description**: Retrieves stored bot logs. Logs are kept in memory (last 100 entries by default).
    *   **Query Parameters (Optional)**:
        *   `level=<LEVEL_STRING>` (e.g., `INFO`, `WARN`, `ERROR`, `DEBUG`) - Filters logs by level.
        *   `module=<MODULE_STRING>` (e.g., `system`, `api_command`, `telegram_handler`) - Filters logs by module (case-insensitive).
    *   **Response (200 OK)**: An array of log objects.
        ```json
        [
          {
            "timestamp": "2023-10-27T10:20:30.123Z",
            "level": "INFO",
            "module": "system",
            "message": "Bot starting..."
          },
          // ... more log entries
        ]
        ```
    *   **Error Response (500 Internal Server Error)**:
        ```json
        {
          "success": false,
          "error": "Failed to retrieve logs",
          "details": "<error_details>"
        }
        ```

4.  **POST `/api/command`**
    *   **Description**: Receives a JSON command to be processed by the bot. Commands are currently saved to a file.
    *   **Request Body (application/json)**:
        ```json
        {
          "type": "command_type_string",
          "module": "target_module_string",
          "args": { /* command-specific arguments */ },
          "id": "unique_command_id_string_or_int"
        }
        ```
    *   **Response (200 OK - Command Saved Successfully)**:
        ```json
        {
          "success": true,
          "message": "Command received and saved.",
          "file_path": "commands/api_commands/mod_general_api/api_20231027_102233_456789_some_id.json"
        }
        ```
    *   **Error Responses**:
        *   `400 Bad Request`: Invalid JSON structure, missing fields, or incorrect field types.
            ```json
            {
              "success": false,
              "error": "Missing required field(s): type"
            }
            ```
        *   `415 Unsupported Media Type`: Request body is not JSON.
            ```json
            {
              "success": false,
              "error": "Invalid request: Content-Type must be application/json"
            }
            ```
        *   `500 Internal Server Error`: Server-side error during processing.
            ```json
            {
              "success": false,
              "error": "Failed to process command due to an internal error."
            }
            ```
