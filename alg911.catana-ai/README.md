# Katana AI Concierge - Project Directory

This directory contains the core files and modules for the Katana AI Concierge project.
Katana is envisioned as a multi-purpose agent with a focus on psychoanalysis, routine automation, neuro-simulation, and civilizational design through Sapiens Coin.

## Project Vision (Summary)

Katana aims to integrate several key areas:
- Core operational logic (NAVIREX CORE, FlowShield)
- System integrations and automation (n8n, Telegram, Google Drive)
- Intelligent agents (SDK, SC-Trader)
- Psychoactive and behavioral modules (Neuro-Refueling, Mind Clearing)
- Sapiens Coin and civilizational contour (SC Simulator, Katana-Philosopher)
- Interaction protocols (Julius/structured commands)

## Current Directory Structure and Components

- **`katana.commands.json`**: Stores structured commands for Katana, interaction requests, and pending tasks. This is a primary interface for programmatic interaction.
- **`tasklist.md`**: A markdown file for tracking broader development tasks and ideas for Katana.
- **`katana_events.log`**: A plain text log file recording system events, agent actions, and simulated interactions.
- **`katana_agent.py`**: A Python script representing the initial Katana Agent SDK. It processes commands from `katana.commands.json` and logs its actions.
- **`rclone.conf`**: A placeholder configuration file for rclone, intended for cloud synchronization of this directory.
- **`sync_to_cloud.sh`**: A shell script to (simulate) synchronize this directory's contents to a cloud provider using rclone.

### Modules (Scaffolded)

- **`neuro_refueling/`**: Placeholder for the "Нейро-Дозаправка" (Neuro-Refueling) module.
  - `README.md`: Module description.
  - `alternatives_log.json`: Example data structure for logging ethanol alternatives and user experiences.
- **`mind_clearing/`**: Placeholder for the "Модуль Очистки Сознания" (Mind Clearing) module.
  - `README.md`: Module description.
  - `thought_patterns.json`: Example data structure for diagnosing and managing background thoughts.

## Next Steps

Further development will involve:
- Implementing the logic within `katana_agent.py` to act upon more command types.
- Developing the actual n8n/Telegram integrations.
- Setting up and testing real cloud synchronization with rclone.
- Populating and developing the scaffolded modules (`neuro_refueling`, `mind_clearing`).
- Beginning design and implementation of other core modules as outlined in the project vision.

## Katana UI Dashboard & Backend Server

A React-based UI dashboard (`katana-dashboard-ui/`) has been developed to provide a web interface for monitoring and interacting with the Katana agent. This UI communicates with a dedicated Python backend server.

### UI Backend Server (`katana_ui_server.py`)

-   **Purpose**: Acts as a bridge between the React UI and the core Katana agent\'s files (`katana.commands.json`, `katana_events.log`, `katana_memory.json`). It uses Flask and Flask-SocketIO for handling HTTP requests and real-time WebSocket communication.
-   **Location**: `alg911.catana-ai/katana_ui_server.py`
-   **Key Modules**:
    -   `backend/socket_handlers.py`: Contains the logic for handling specific WebSocket events from the UI (e.g., sending commands, pinging the agent).
-   **Dependencies**:
    -   Flask
    -   Flask-SocketIO
    -   watchdog (for monitoring log file changes)
    -   psutil (for system metrics like CPU/RAM usage for the ping command)
    -   pytest, pytest-flask, python-socketio[client] (for running tests)
    *It is recommended to use a Python virtual environment and install dependencies from `requirements.txt` (see below).*
-   **Running the Server**:
    Navigate to the `alg911.catana-ai` directory and run:
    ```bash
    python katana_ui_server.py
    ```
    The server typically runs on `http://localhost:5050`.
-   **Testing the Backend**:
    Ensure you have `pytest` and `pytest-flask` installed. From the `alg911.catana-ai` directory, run:
    ```bash
    PYTHONPATH=. pytest
    ```
    (Setting `PYTHONPATH=.` ensures that modules within `alg911.catana-ai`, like `backend.socket_handlers`, can be correctly imported by the test files.)

### Agent-Side Command Handling (`katana_agent.py`)

The `katana_agent.py` script has been updated with new functions to handle commands initiated from the UI:
-   `handle_agent_get_config()`: Retrieves agent configuration and stores it in memory.
-   `handle_agent_reload_settings()`: Placeholder for reloading settings (currently re-triggers file initialization).
-   `handle_agent_ping_received()`: Processes ping commands logged by the UI backend.
-   `process_agent_command(command_object)`: A dispatcher function that calls the appropriate handler based on a command\'s \'action\'.

**Note**: For these commands to be fully processed by `katana_agent.py`, a main command processing loop needs to be implemented or activated within `katana_agent.py` to continuously read `katana.commands.json` and execute new commands using `process_agent_command()`.
