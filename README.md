# Katana Project

This project consists of a Telegram bot and a React-based user interface.

## Project Structure

-   `/bot`: Contains the Python code for the Telegram bot.
    -   `katana_bot.py`: The main script for the bot.
    -   `commands/`: Directory where the bot stores received commands.
-   `/ui`: Contains the React (Vite + TypeScript) frontend application. This is the primary user interface.
-   `/legacy_ui`: Contains an older or alternative version of the UI. Its specific purpose may need further clarification, but it's not the primary interface. (Note: Dependencies in `legacy_ui/package.json` were reviewed and found to be up-to-date according to their specified version ranges. No critical updates were immediately necessary, and further dependency upgrades are deferred due to its legacy status.)
-   `.gitignore`: Specifies intentionally untracked files that Git should ignore.

## Bot Instructions

The Telegram bot is built with Python and `pyTelegramBotAPI`.

### Prerequisites

-   Python 3.x
-   Dependencies listed in `bot/requirements.txt` (e.g., `pyTelegramBotAPI`, `Flask`, `Flask-CORS`). These can be installed by running `pip install -r bot/requirements.txt` within the `bot` directory (ideally in a virtual environment).
    *Note: As of the last review, dependencies like Flask-CORS were updated to their latest stable versions (e.g., Flask-CORS from >=3.0 to >=4.0.0). It's good practice to periodically review and update dependencies as outlined in the "Local Development Best Practices" section.*

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

### Testing the Bot

It's recommended to run tests to ensure the bot is functioning as expected. We use `pytest` for testing.

1.  Ensure you have `pytest` installed in your virtual environment:
    ```bash
    pip install pytest
    ```
2.  Navigate to the root project directory if you are not already there.
3.  Run the tests:
    ```bash
    python -m pytest bot/tests
    ```

### Linting the Bot Code

Linting helps maintain code quality and catch potential errors. We recommend using `flake8` and `pylint`.

1.  Ensure you have `flake8` and `pylint` installed:
    ```bash
    pip install flake8 pylint
    ```
2.  Navigate to the root project directory.
3.  Run the linters:
    ```bash
    flake8 bot
    pylint bot
    ```
    Address any issues reported by the linters.

### Code Coverage

To check how much of your code is covered by tests, you can use `pytest-cov`.

1.  Ensure you have `pytest-cov` installed:
    ```bash
    pip install pytest-cov
    ```
2.  Navigate to the root project directory.
3.  Run pytest with the coverage option:
    ```bash
    python -m pytest --cov=bot bot/tests
    ```
    This will output a coverage report to the console. For a more detailed HTML report, you can run:
    ```bash
    python -m pytest --cov=bot --cov-report=html:cov_html bot/tests
    ```
    Then open `cov_html/index.html` in your browser.

### Local Development Best Practices

To ensure a smooth development experience and maintain a healthy codebase, follow these best practices:

*   **Use Virtual Environments**: Always use a Python virtual environment (as mentioned in the "Running the Bot" section) to manage project dependencies and avoid conflicts with system-wide packages.
*   **Keep Dependencies Up-to-Date**: Regularly update your dependencies to their latest compatible versions:
    ```bash
    pip install --upgrade -r bot/requirements.txt
    ```
    Test thoroughly after updating.
*   **Write Unit Tests**: Write unit tests for new features and bug fixes. Store your tests in the `bot/tests` directory. This helps ensure your code is reliable and makes refactoring safer.
*   **Follow Linting Rules**: Adhere to the linting rules enforced by `flake8` and `pylint` to maintain consistent code style and quality.
*   **Commit Regularly**: Make small, atomic commits with clear messages. This makes it easier to track changes and revert them if necessary.

## UI (React App) Instructions

The main user interface is a React application built with Vite and TypeScript, located in the `/ui` directory.

### Prerequisites

-   Node.js and npm (or yarn).
-   Project dependencies listed in `ui/package.json`. These can be installed by running `npm install` (or `yarn install`) in the `ui` directory.
    *Note: Dependencies are periodically reviewed. For example, `tailwindcss` was updated from `^3.3.2` to `^3.4.17` to bring in the latest features and fixes within the v3 range. It's good practice to periodically review and update dependencies as outlined in the "Local Development Best Practices (UI)" section.*

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

### Testing the UI

Testing is crucial for ensuring the UI behaves as expected. While this project doesn't have a pre-configured test runner in `ui/package.json`, a common setup for React projects involves using libraries like [Jest](https://jestjs.io/) and [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/).

1.  **Set up a test runner**: If not already set up, you would typically install these as dev dependencies:
    ```bash
    cd ui
    npm install --save-dev jest @types/jest @testing-library/react @testing-library/jest-dom
    # or
    yarn add --dev jest @types/jest @testing-library/react @testing-library/jest-dom
    ```
2.  **Configure Jest**: Create a `jest.config.js` or add Jest configuration to `package.json`.
3.  **Write tests**: Create test files (e.g., `MyComponent.test.tsx`) for your components and utility functions.
4.  **Run tests**: Add a test script to your `ui/package.json`, for example:
    ```json
    "scripts": {
      // ... other scripts
      "test": "jest"
    }
    ```
    Then run the tests:
    ```bash
    cd ui
    npm test
    # or
    yarn test
    ```

### Linting the UI Code

The UI project is set up with ESLint to enforce code quality and consistency, as indicated in `ui/package.json`.

1.  Ensure all development dependencies, including ESLint and its plugins, are installed:
    ```bash
    cd ui
    npm install
    # or
    yarn install
    ```
2.  Run the linter from the `ui` directory:
    ```bash
    npm run lint
    # or
    yarn lint
    ```
    Address any issues reported by ESLint. You can find ESLint configuration in `ui/.eslintrc.js` (or a similar file like `eslint.config.js` as suggested in `ui/README.md`).

### Local Development Best Practices (UI)

For a productive and maintainable UI development workflow:

*   **Keep Node.js and Package Manager Updated**: Ensure you have a recent LTS version of Node.js. Keep npm or yarn updated:
    ```bash
    # For npm
    npm install -g npm@latest
    # For yarn (if you use Yarn 1.x)
    yarn set version stable
    ```
*   **Regularly Update Dependencies**: Keep your project dependencies current. Navigate to the `ui` directory and run:
    ```bash
    npm update
    # or
    yarn upgrade
    ```
    Review changes and test thoroughly after updates, as breaking changes can occur.
*   **Write Component and Utility Tests**: Develop tests for your React components (interaction, rendering) and any utility functions. This helps catch regressions and validates functionality.
*   **Follow Linting Rules**: Adhere to the ESLint rules configured for the project. Integrate linting into your editor for real-time feedback.
*   **Structure Components Logically**: Organize your components in a clear and maintainable folder structure (e.g., feature-based or atomic design).
*   **Manage State Effectively**: Choose a state management solution appropriate for the application's complexity (e.g., React Context, Zustand, Redux Toolkit).
*   **Optimize Performance**: Be mindful of performance aspects like bundle size, rendering performance, and efficient data fetching. Utilize tools like React DevTools for profiling.

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
