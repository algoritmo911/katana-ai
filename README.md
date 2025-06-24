# katana-ai

## Logging System & UI

This project includes a comprehensive logging system with a user interface for viewing and configuring logs.

### Features

*   **Centralized Backend Logging:** All Python components utilize a standardized logging setup (`katana/logging_config.py`) that outputs to both console and a rotating file (`katana_events.log`).
*   **Log Viewer UI:** A dedicated "Logs" page in the web interface (`/logs`) allows users to:
    *   View log entries. The current implementation fetches logs on demand. Real-time polling or WebSocket updates are potential future enhancements.
    *   Paginate through logs.
    *   Filter logs by level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    *   Search log messages for specific keywords.
*   **Log Configuration UI:** From the "Logs" page, users can:
    *   View the current application-wide logging level and the path to the log file.
    *   Change the application's logging level dynamically.

### Logging API Endpoints

The backend exposes the following API endpoints (typically running on `http://localhost:8000` if `katana/api/server.py` is run directly):

*   **`GET /api/logs`**: Fetches log entries.
    *   Query Parameters:
        *   `page` (int, default: 1): For pagination.
        *   `limit` (int, default: 100): Entries per page.
        *   `level` (str, optional): Filter by log level (e.g., "INFO", "ERROR"). Case-insensitive on the backend.
        *   `search` (str, optional): Filter by a search term within log messages. Case-insensitive.
    *   Returns: JSON array of log objects, newest first. Each object contains `timestamp`, `level`, `module`, `message`.

*   **`GET /api/logs/status`**: Retrieves the current logging status.
    *   Returns: JSON object with `level` (current log level string) and `log_file` (path to log file).

*   **`POST /api/logs/level`**: Sets the application's global log level.
    *   Request Body (JSON): `{ "level": "DEBUG" }` (valid levels: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
    *   Returns: Success or error message.

### Log Monitoring in Development

For details on how to monitor and analyze `katana_events.log` in a development environment using tools like `jq`, and for notes on integrating with more advanced log management systems, please see:
[Dev Log Monitoring Guide](./docs/logging_monitoring.md)

---

**IMPORTANT: Current Environmental Limitations & Testing Status**

As of the latest updates, there are significant environmental blockers that prevent the full execution of the testing suite.

*   **Package Installation Timeouts:** Attempts to install both Python packages (via `pip`, e.g., `httpx` for backend tests) and Node.js packages (via `npm`, e.g., Jest, React Testing Library, Cypress for frontend tests) consistently time out after approximately 400 seconds. This appears to be a hard limit or severe network/resource throttling within the execution environment.
*   **Impact on Testing:**
    *   **Backend API Tests:** Written (`katana/api/tests/test_api_server.py`) but **cannot be run** due to the inability to install `httpx`.
    *   **Frontend Unit Tests:** Configuration files for Jest/React Testing Library are in place (`katana/ui/jest.config.js`, etc.). Test files have been drafted for `LogViewer.tsx`, `LogConfiguration.tsx`, and `LogsPage.tsx` (`katana/ui/src/components/__tests__/` and `katana/ui/src/pages/__tests__/`). However, these tests **cannot be run** because the necessary `npm` packages (Jest, RTL) could not be installed.
    *   **End-to-End (E2E) Tests:** Scenarios have been outlined for Cypress (see `katana/tests/e2e_scenarios_logging.md`). However, Cypress setup (via `npm install`) is also expected to fail under the current environmental constraints.

**Resolving these installation timeouts is crucial for enabling the test suites.**

---

### Running Tests (If Environment is Functional)

**1. Backend API Tests:**

*   **Prerequisites:** Python, `pip`, and a functional environment allowing package installation.
*   **Setup:**
    ```bash
    # From the project root
    # (Optional: Create and activate a virtual environment)
    # python -m venv venv
    # source venv/bin/activate

    # Install required packages for the API server and tests
    pip install fastapi "uvicorn[standard]" httpx pytest

    # Ensure PYTHONPATH is set to include the project root for imports like 'katana.api.server'
    # This is often needed when running pytest from the root directory.
    # export PYTHONPATH=.
    ```
*   **Execution:**
    ```bash
    # From the project root, ensuring PYTHONPATH includes the current directory
    PYTHONPATH=. pytest katana/api/tests/test_api_server.py
    ```

**2. Frontend Unit Tests:**

*   **Prerequisites:** Node.js, `npm`, and a functional environment allowing `npm install`.
*   **Setup (from `katana/ui/` directory):**
    ```bash
    cd katana/ui
    npm install # This would install Jest, RTL, and other devDependencies
    ```
*   **Execution (from `katana/ui/` directory):**
    ```bash
    npm test
    ```
    This will run Jest and look for test files (e.g., `*.test.tsx`).

**3. Frontend End-to-End Tests (Cypress - Conceptual):**

*   **Prerequisites:** Node.js, `npm`, a functional environment allowing `npm install`, and the application (frontend and backend API) running.
*   **Detailed Scenarios:** See `katana/tests/e2e_scenarios_logging.md`.
*   **Setup (from `katana/ui/` directory):**
    ```bash
    cd katana/ui
    npm install cypress --save-dev # Or as per project's Cypress setup
    ```
*   **Execution (from `katana/ui/` directory, typically):**
    ```bash
    npx cypress open # To open the Cypress Test Runner
    # Or
    npx cypress run # To run tests headlessly
    ```

---