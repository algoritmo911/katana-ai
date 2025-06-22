# KatanaState Architecture and Memory Module

This document describes the architecture of Katana's memory module, primarily centered around the `KatanaState` class and the `katana_state.json` file.

## 1. Purpose

The Katana memory module is responsible for persisting and managing the bot's state across sessions. This includes:
-   Conversation history for each chat.
-   User-specific settings.
-   Global bot metrics.
-   Ensuring data can be backed up and potentially restored.

## 2. Core Component: `katana_state.json`

This is the primary file where all persistent state of the Katana bot is stored. It's a JSON file, typically located at the root of the bot's working directory (or as configured).

### Structure of `katana_state.json`:

The JSON file has the following top-level keys:

-   **`global_metrics`**: An object containing bot-wide metrics.
    -   Example: `{"version": "1.0", "last_reset": "YYYY-MM-DDTHH:MM:SS.ffffff"}`
-   **`chat_histories`**: An object where each key is a `chat_id` (string) and the value is an object representing the chat history for that chat.
    -   Each chat history object contains a single key:
        -   `"messages"`: A list of message objects.
            -   Each message object has:
                -   `"sender"`: (string) Who sent the message (e.g., "user", "katana", "system_event").
                -   `"text"`: (string) The content of the message.
                -   `"timestamp"`: (string) ISO 8601 formatted UTC timestamp.
    -   Example:
        ```json
        "chat_histories": {
          "12345": {
            "messages": [
              {"sender": "user", "text": "Hello", "timestamp": "..."},
              {"sender": "katana", "text": "Hi there!", "timestamp": "..."}
            ]
          }
        }
        ```
-   **`user_settings`**: An object where each key is a `chat_id` (string) and the value is an object containing settings for that user.
    -   Example:
        ```json
        "user_settings": {
          "12345": {"notifications": true, "language": "ru"}
        }
        ```

## 3. Key Class: `KatanaState` (in `bot/katana_state.py`)

The `KatanaState` class is the Python interface for managing the data in `katana_state.json`.

### Initialization:

-   `state = KatanaState(state_file_path: Path = DEFAULT_STATE_FILE)`
-   On initialization, it attempts to load data from the specified `state_file_path`.
-   If the file doesn't exist or is corrupted, it initializes with an empty state structure and creates/overwrites the file.

### Key Methods:

-   **State Persistence:**
    -   `save_state()`: Writes the current in-memory state to `state_file_path`. This is typically called automatically by methods that modify the state (e.g., `add_chat_message`, `update_user_setting`).
    -   `backup_state(backup_file_path: Path)`: Saves the current state to a *specified* backup file path. This is useful for creating explicit backups. The parent directory for the backup path will be created if it doesn't exist.

-   **Chat History Management:**
    -   `get_chat_history(chat_id: str) -> ChatHistory`: Retrieves a `ChatHistory` object for the given `chat_id`. If no history exists for the chat, a new empty `ChatHistory` object is created and returned.
    -   `add_chat_message(chat_id: str, sender: str, text: str)`: Adds a new message to the specified chat's history and saves the state. The timestamp is generated automatically if not provided (though the current public method doesn't take a timestamp argument directly, `ChatHistory.add_message` does).
    -   `clear_chat_history(chat_id: str)`: Clears all messages from the specified chat's history and saves the state.

-   **User Settings Management:**
    -   `get_user_settings(chat_id: str) -> Dict[str, Any]`: Retrieves the settings dictionary for the user. If no settings exist, default settings (e.g., `{"notifications": True, "language": "ru"}`) are created and returned.
    -   `update_user_setting(chat_id: str, setting_key: str, setting_value: Any)`: Updates a specific setting for a user and saves the state.

-   **Global Metrics Management:**
    -   `update_global_metric(key: str, value: Any)`: Adds or updates a global metric and saves the state.

### Internal Helper Class: `ChatHistory`

-   A simple class used by `KatanaState` to manage the list of messages for a single chat.
-   Provides `add_message(sender, text, timestamp=None)`, `to_dict()`, and `from_dict()` methods.

## 4. Backup Mechanism (Implemented in `katana_bot.py`)

While `KatanaState` provides the `backup_state` method, the triggering of backups is handled in `katana_bot.py`.

-   **Trigger:** Backups are currently triggered after a configurable number of messages (`BACKUP_INTERVAL_MESSAGES`) are processed by the `handle_message_impl` function.
-   **Location:** Backups are saved in a directory specified by `BACKUP_DIR` (e.g., `katana_backups/`).
-   **Filename:** Backup files are timestamped (e.g., `katana_state_backup_YYYYMMDD_HHMMSS.json`).
-   **Process:** When triggered, `katana_bot.py` calls `katana_state.backup_state(backup_path)`.

## 5. Interaction and Extension

-   **Primary Interaction:** The `katana_bot.py` module interacts with `KatanaState` by creating an instance of it and calling its public methods to manage state based on user interactions and bot events.
-   **Extending Functionality:**
    -   **New State Data:** To add new types of persistent data, modify the `KatanaState` class:
        1.  Add new attributes to store the data (e.g., `self.new_data_collection = {}`).
        2.  Update `_load_state()` to load this data from the JSON structure.
        3.  Update `_initialize_empty_state()` to provide default values for this new data.
        4.  Update `save_state()` and `backup_state()` to include this new data in the `data_to_save` dictionary.
        5.  Add new public methods to `KatanaState` to manage this data.
    -   **Changing Storage:** While currently JSON-based, `KatanaState` could be refactored to use a different backend (e.g., SQLite, a NoSQL database) by changing the implementation of its loading and saving methods, while ideally keeping its public API consistent.

## 6. Current Considerations

-   **Save Frequency:** State is currently saved to `katana_state.json` after almost every modification. This ensures data integrity but might be I/O intensive for very high-traffic bots. Future optimizations could include batching saves or using a more robust storage solution.
-   **Concurrency:** The current file-based approach is simple. If the bot were to become multi-threaded or multi-process in a way that involves concurrent writes to the state, proper file locking or a database solution would be necessary. `telebot`'s default polling is single-threaded for message handling, which mitigates this for now.
-   **Error Handling:** Basic error handling for file I/O is present (printing errors). More sophisticated error handling and recovery strategies could be added.

This documentation provides a foundational understanding of Katana's memory system.
