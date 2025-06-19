# Katana: Your Integrated AI Ecosystem ⚔️

Welcome to the Katana project! Katana is envisioned as a multifaceted AI system, a "living organism" designed for maximum efficiency, rapid iteration, and robust, scalable operation. It aims to serve as a personal AI operator, integrating various data sources and providing intelligent assistance across diverse domains.

## Philosophy
Katana is built on the principles of:
- **Modularity & Extensibility**: Components are designed to be independent yet interconnected, allowing for easy expansion and integration of new capabilities.
- **Robustness & Resilience**: Emphasis on error handling, data integrity, and stable operation.
- **User-Centric Design**: Focus on providing clear interfaces and intuitive interactions.
- **Data-Driven Memory**: Leveraging diverse data sources to build a comprehensive and evolving knowledge base for the AI.
- **Iterative Development**: Rapidly developing, testing, and refining components to achieve practical results at each stage.

## Project Architecture (`katana/`)

The Katana project is organized into the following main components:

-   **`bot/`**:
    -   `katana_bot.py`: The primary user-facing AI bot, currently integrated with OpenAI (GPT models) and accessible via Telegram. Handles natural language interaction.
-   **`mci_agent/`**:
    -   `katana_agent.py`: The Multi-layered Command Interface (MCI) agent. Processes commands from individual JSON files dropped into its `commands/` directory. Manages its own `logs/`, `status/`, `processed/` commands, and `modules/` (for file-based command handlers).
-   **`ui/`**:
    -   Contains the React + TypeScript frontend application (previously `katana-secrets-ui`) built with Vite and styled with Tailwind CSS. This UI provides:
        -   An interactive chat interface (dashboard).
        -   A "Connection Center" for managing data source integrations.
        -   A display for harvested secrets (future functionality).
-   **`core/`**:
    -   `cli_agent/`: The original Katana Core MVP, a command-line interface (CLI) agent with basic command execution, memory, and status tracking.
    -   *(Future)*: This directory will house shared algorithms, core logic (e.g., NAVIREX, FlowShield), and fundamental utilities used across multiple Katana components.
-   **`services/`**:
    *   `secrets_harvester/`: Python utility to harvest secrets (API keys, tokens) from Google Keep (`harvester.py`) and iCloud Notes (`icloud_sync.py`), saving them to `secrets_temp.json`.
    *   `api_integrations/`: Python modules for direct API interaction with external services like Gmail (`gmail_service.py`) and GitHub (`github_service.py`) for data ingestion into Katana's memory.
-   **`data/`**:
    *   Intended for storing data models, YAML configurations, non-sensitive datasets, and potentially templates for secrets (actual secrets should be managed via secure methods like Google Secret Manager or environment variables and be in `.gitignore`).
-   **`tests/`**:
    *   Top-level directory for integration tests that span multiple Katana components. Individual components (e.g., `services/secrets_harvester/tests/`) also contain their own unit tests.

## Current Status & Next Steps

-   **Core AI Interaction**: The `katana/bot/katana_bot.py` (OpenAI version) provides the primary chat interface via Telegram.
-   **Command Processing Backend**: The `katana/mci_agent/katana_agent.py` offers a file-based command processing system.
-   **Data Harvesting**: `katana/services/secrets_harvester/` can collect secrets from Google Keep and iCloud. `katana/services/api_integrations/` has initial modules for Gmail and GitHub.
-   **UI**: `katana/ui/` provides an interactive chat UI, a Connection Center page, and basic routing.

Key areas for ongoing development include:
-   Full integration between the `katana_bot.py` and the `mci_agent.py` (e.g., Telegram commands triggering MCI agent actions).
-   Implementing the data ingestion pipelines from `api_integrations` into a persistent Katana memory.
-   Building out the UI features for managing connections, displaying harvested data, and interacting with Katana's memory.
-   Developing the advanced AI capabilities outlined in "Katana Core 0.2 – Awakening of Memory" and beyond.

## Getting Started

1.  **Clone the Repository** (if applicable).
2.  **Set up Python Environment**: Each Python component (in `bot/`, `mci_agent/`, `core/cli_agent/`, `services/`) may have its own `requirements.txt` or dependencies. Install them as needed (e.g., `pip install -r requirements.txt`).
    *   `katana/bot/katana_bot.py` requires: `python-telegram-bot openai` (specify version for openai, e.g. "openai<1.0.0" or "openai>=1.0.0" based on bot's code).
    *   `katana/services/secrets_harvester/` requires: `gkeepapi pyicloud`.
    *   `katana/services/api_integrations/` requires: `google-api-python-client google-auth-httplib2 google-auth-oauthlib PyGithub`.
3.  **Set up UI Environment**:
    ```bash
    cd katana/ui
    npm install
    # To run dev server:
    npm run dev
    ```
4.  **Configure Credentials & API Keys**:
    *   **Telegram Bot**: Set `KATANA_TELEGRAM_TOKEN` environment variable (used by `katana/bot/katana_bot.py`).
    *   **OpenAI**: Set `OPENAI_API_KEY` environment variable (used by `katana/bot/katana_bot.py`).
    *   **Secrets Harvester (Google Keep)**: Set `GKEEP_USERNAME` and `GKEEP_PASSWORD` (App Password for 2FA) environment variables for `katana/services/secrets_harvester/harvester.py`.
    *   **Secrets Harvester (iCloud)**: Set `ICLOUD_USERNAME` and `ICLOUD_PASSWORD` (App-Specific Password recommended) for `katana/services/secrets_harvester/icloud_sync.py`.
    *   **API Integrations (Gmail)**: Follow instructions in `katana/services/api_integrations/README.md` to set up `credentials.json` for OAuth.
    *   **API Integrations (GitHub)**: Set `GITHUB_PAT` environment variable.
5.  **Run Components**:
    *   Katana Bot: `python katana/bot/katana_bot.py`
    *   MCI Agent: `cd katana/mci_agent && python katana_agent.py --loop` (adjust path if running from project root)
    *   UI: `cd katana/ui && npm run dev`
    *   Harvesters/Integrations: Run scripts directly as needed, e.g., `python katana/services/secrets_harvester/harvester.py`.

Refer to the README files within each component's directory for more specific instructions.
