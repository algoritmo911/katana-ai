# Katana Dashboard UI

This is a React-based user interface for monitoring and interacting with the Katana AI agent.

## Overview

The Katana Dashboard provides:
- Real-time viewing of Katana agent event logs.
- Display of Katana agent status, memory, and configuration.
- Controls to send commands to the Katana agent (e.g., ping, reload settings, custom commands).

It communicates with a Python-based backend server (`katana_ui_server.py`) via WebSockets.

## Prerequisites

- Node.js (v16.x or later recommended)
- npm (usually comes with Node.js)

## Setup

1.  Navigate to the `katana-dashboard-ui` directory:
    ```bash
    cd path/to/your/project/katana-dashboard-ui
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```

## Running the Development Server

1.  **Ensure the backend server (`katana_ui_server.py`) is running.** This server is typically found in the `alg911.catana-ai` directory and runs on `http://localhost:5050` by default.
2.  Start the React development server:
    ```bash
    npm start
    ```
    This will usually open the dashboard in your default web browser at `http://localhost:3000`.

## Project Structure

-   `src/App.js`: Main application component, sets up layout and routing (if any).
-   `src/components/`: Contains reusable React components:
    -   `LogViewer.js`: Displays Katana event logs.
    -   `KatanaStatus.js`: Shows agent status, memory, config, and connection info.
    -   `CommandSender.js`: UI for sending custom commands to the agent.
    -   `KatanaControls.js`: UI for predefined agent control actions (Ping, Reload Settings).
-   `src/index.js`: Entry point for the React application.

## WebSockets Connection

The UI connects to the backend WebSocket server defined by `SOCKET_SERVER_URL` in the component files (default: `http://localhost:5050`).

## Running Tests

To run the Jest unit tests:
```bash
npm test
```
This will launch the test runner in interactive watch mode.

EOF
