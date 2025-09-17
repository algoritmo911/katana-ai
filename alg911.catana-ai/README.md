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
