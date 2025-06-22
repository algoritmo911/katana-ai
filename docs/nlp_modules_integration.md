# Integrating New NLP Modules

This document outlines the process for adding and configuring new NLP (Natural Language Processing) provider modules to this project.

## 1. NLP Provider Interface

All NLP provider modules must adhere to a specific interface defined by the `NLPProvider` abstract base class located in `nlp_providers/base.py`. Your new provider class must inherit from `NLPProvider` and implement all its abstract methods.

Key methods to implement:

*   **`__init__(self, config: dict = None)` (Optional but Recommended)**:
    *   The constructor can optionally accept a `config` dictionary. This dictionary will contain provider-specific settings defined in `config/settings.yaml`.
    *   It's good practice to store this config or relevant parts of it within your provider instance.

*   **`@property name(self) -> str`**:
    *   This property must return a string representing the unique name of your NLP provider (e.g., "MyAwesomeNLPProvider"). This name is used for logging and identification.

*   **`get_intent(self, text: str) -> dict`**:
    *   **Input**: `text` (str) - The raw user input string.
    *   **Output**: A dictionary containing:
        *   `"intent_name"` (str): The identified intent (e.g., "get_weather", "play_music").
        *   `"confidence"` (float): A score between 0.0 and 1.0 indicating the provider's confidence in this intent.
        *   Example: `{"intent_name": "greeting", "confidence": 0.95}`
        *   If no intent is found, you might return `{"intent_name": "unknown_intent", "confidence": 0.0}` or similar.

*   **`get_slots(self, text: str, intent: str = None) -> dict`**:
    *   **Input**:
        *   `text` (str) - The raw user input string.
        *   `intent` (str, optional) - The intent name that might have been pre-identified for this text. Some providers can use this to improve slot extraction accuracy.
    *   **Output**: A dictionary where keys are slot names (str) and values are the extracted slot values (any type, typically str, int, list).
        *   Example: `{"location": "Paris", "date": "tomorrow"}`
        *   If no slots are found, return an empty dictionary `{}`.

*   **`process(self, text: str) -> dict`**:
    *   **Input**: `text` (str) - The raw user input string.
    *   **Output**: A dictionary containing both intent and slots, structured as follows:
        ```json
        {
            "intent": {"intent_name": "book_flight", "confidence": 0.88},
            "slots": {"destination": "London", "departure_date": "2024-12-25"}
        }
        ```
    *   This method can be more efficient for providers that process intent and slots simultaneously. If your provider benefits from this, implement it. Otherwise, you can provide a basic implementation that calls `get_intent` and `get_slots` sequentially (see `DummyProvider` for an example). The `CommandParser` will attempt to use this method first.

## 2. Creating Your Provider Module

1.  **Create a new Python file** in the `nlp_providers/` directory (e.g., `my_new_provider.py`).
2.  **Define your provider class** within this file, ensuring it inherits from `NLPProvider` and implements all required methods.

    ```python
    # nlp_providers/my_new_provider.py
    from nlp_providers.base import NLPProvider
    # Import any other necessary libraries for your provider (e.g., requests, specific SDKs)

    class MyNewProvider(NLPProvider):
        def __init__(self, config: dict = None):
            self._name = "MyNewProvider"
            self.api_key = None
            if config:
                self.api_key = config.get("api_key")
            # ... other initializations ...

        @property
        def name(self) -> str:
            return self._name

        def get_intent(self, text: str) -> dict:
            # Your logic to call the external NLP service or process text
            # Example:
            # response = self.call_external_api(text, "intent")
            # return {"intent_name": response.get("intent"), "confidence": response.get("score")}
            pass

        def get_slots(self, text: str, intent: str = None) -> dict:
            # Your logic to call the external NLP service or process text
            # Example:
            # response = self.call_external_api(text, "slots", intent_context=intent)
            # return response.get("entities")
            pass

        def process(self, text: str) -> dict:
            # Recommended: Implement efficient combined processing if possible
            # Otherwise, call get_intent and get_slots:
            intent_data = self.get_intent(text)
            slots_data = self.get_slots(text, intent_data.get("intent_name"))
            return {
                "intent": intent_data,
                "slots": slots_data
            }

        # ... any helper methods ...
    ```

## 3. Configuration

1.  **Open the configuration file**: `config/settings.yaml`.
2.  **Activate your provider**:
    *   Update the `active_nlp_provider` key. The value should be a string in the format `"your_module_name.YourClassName"`.
        For example, if your file is `my_new_provider.py` and your class is `MyNewProvider`, you would set:
        ```yaml
        active_nlp_provider: "my_new_provider.MyNewProvider"
        ```
3.  **Add provider-specific configuration (if any)**:
    *   If your provider requires API keys, endpoints, or other settings, add a new section to `settings.yaml` with a key matching your module name (`my_new_provider` in this example).
        ```yaml
        # ... other settings ...

        active_nlp_provider: "my_new_provider.MyNewProvider"

        my_new_provider:
          api_key: "YOUR_SECRET_API_KEY"
          endpoint_url: "https://api.mynewprovider.com/v1/process"
          timeout: 10

        # ... other provider configs ...
        ```
    *   Your provider's `__init__` method will receive the dictionary under `my_new_provider` as its `config` argument.

## 4. Dependencies

*   If your new NLP provider requires external Python libraries (e.g., an SDK for a commercial NLP service, specific machine learning libraries), list them in a `requirements.txt` file at the project root or ensure they are installed in your project's environment.
    *Consider updating the main `requirements.txt` or providing setup instructions.*

## 5. Testing

*   It is highly recommended to add unit tests for your new provider in the `tests/` directory. Create a new test file (e.g., `tests/test_my_new_provider.py`).
*   Test various inputs, edge cases, and ensure the output format matches the interface requirements.
*   You can run the `parser/command_parser.py` script (e.g., `python parser/command_parser.py`) after configuring your provider to see it in action with some sample phrases.

By following these steps, you can integrate various NLP services into the system, making it flexible and adaptable to different NLP capabilities.
