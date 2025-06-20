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
