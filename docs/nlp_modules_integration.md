# Integrating New NLP Modules

This document outlines the process for adding and configuring new NLP (Natural Language Processing) provider modules to this project. The system supports both basic NLP providers and advanced providers with richer capabilities.

## 1. NLP Provider Interfaces

There are two main interfaces for NLP providers:

*   **`NLPProvider` (from `nlp_providers.base.py`)**: For basic NLP tasks, primarily focused on single intent and slot extraction.
*   **`AdvancedNLPProvider` (from `nlp_providers.advanced_base.py`)**: Inherits from `NLPProvider` and extends it for more complex scenarios, including multi-intent recognition, context handling, and richer response data.

When creating a new provider, choose the interface that best suits its capabilities. For modern, powerful NLP services (like GPT, Claude, or sophisticated HuggingFace models), `AdvancedNLPProvider` is recommended.

### Key Methods for `NLPProvider`

*   **`__init__(self, config: dict = None)`**:
    *   The constructor receives a `config` dictionary derived from the provider's specific section in `config/settings.yaml`. Use this to initialize API keys, model names, endpoints, etc.
    *   API keys should preferably be loaded from environment variables (see Configuration section).
*   **`@property name(self) -> str`**: Returns the unique name of your provider.
*   **`get_intent(self, text: str) -> dict`**:
    *   Input: `text` (str).
    *   Output: `{"intent_name": str, "confidence": float}`.
*   **`get_slots(self, text: str, intent: str = None) -> dict`**:
    *   Input: `text` (str), optional `intent` (str).
    *   Output: `{"slot_name": value, ...}`.
*   **`process(self, text: str) -> dict`**:
    *   Input: `text` (str).
    *   Output: `{"intent": {"intent_name": ..., "confidence": ...}, "slots": {...}}`.
    *   The `CommandParser` uses this method for basic providers.

### Key Methods for `AdvancedNLPProvider`

Inherits methods from `NLPProvider` but primarily relies on:

*   **`__init__(self, config: dict = None)`**: Same as `NLPProvider`, used for specific setup.
*   **`@property name(self) -> str`**: Same as `NLPProvider`.
*   **`process_advanced(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`**:
    *   **Input**:
        *   `text` (str): The user's input.
        *   `context` (Optional `dict`): Dialogue context, which can include session ID, previous intents, active slots, user preferences, dialogue history, etc. The structure is flexible. Example:
            ```json
            {
                "session_id": "user123_sessionABC",
                "previous_intents": [{"name": "get_weather", "slots": {"location": "Paris"}}],
                "active_slots": {"location": "Paris", "time_constraint": "tomorrow"},
                "user_preferences": {"temperature_unit": "celsius"}
            }
            ```
    *   **Output**: A dictionary with a richer structure. Example:
        ```json
        {
            "intents": [ // List of identified intents, sorted by confidence
                {"intent_name": "book_flight", "confidence": 0.9, "provider_details": {}},
                {"intent_name": "request_hotel", "confidence": 0.7, "provider_details": {}}
            ],
            "slots": {
                "destination": "London",
                "departure_date": "2024-12-25",
                "booking_type": ["flight", "hotel"] // Example of multi-value slot
            },
            "raw_provider_response": { ... }, // Original response from the external service
            "processed_text": "Book a flight and hotel to London for December 25th, 2024", // Text after provider preprocessing
            "language": "en", // Detected language code
            "new_context_elements": { ... } // Optional: elements provider suggests adding/updating in dialogue context
        }
        ```
    *   The `CommandParser` will primarily use this method if the provider is an `AdvancedNLPProvider`. The base methods (`get_intent`, `get_slots`, `process`) in `AdvancedNLPProvider` are adapted to call `process_advanced` and simplify its output, ensuring basic compatibility.

## 2. Creating Your Provider Module

1.  **Create a new Python file** in the `nlp_providers/` directory (e.g., `my_openai_provider.py`).
2.  **Define your provider class**, inheriting from `NLPProvider` or `AdvancedNLPProvider`.
3.  **Implement all required abstract methods.**

    ```python
    # nlp_providers/my_advanced_provider.py
    import os
    from typing import Dict, Any, Optional
    from nlp_providers.advanced_base import AdvancedNLPProvider
    # Import necessary SDKs, e.g., from openai, anthropic, huggingface_hub, etc.

    class MyAdvancedProvider(AdvancedNLPProvider):
        def __init__(self, config: Dict[str, Any]):
            self._name = "MyAdvancedProvider"
            self.config = config

            # Load API key securely (example, actual key name might differ)
            self.api_key = config.get("api_key") # This key is already resolved from env by config.loader
            if not self.api_key:
                # Providers can choose to raise an error or operate in a limited mode.
                print(f"Warning: API key for {self.name} not found. Functionality may be limited.")

            self.model_name = config.get("default_model", "some-default-model")
            # Initialize your NLP client (e.g., OpenAI client, HuggingFace pipeline)
            # self.client = ThirdPartyNLPSDK.Client(api_key=self.api_key)
            print(f"{self.name} initialized with model {self.model_name}.")

        @property
        def name(self) -> str:
            return self._name

        def process_advanced(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            print(f"{self.name} processing text: '{text}' with context: {context is not None}")

            # 1. Prepare request for your external NLP service
            #    - Use self.model_name, self.api_key
            #    - Incorporate `text` and `context` into the API request payload.
            #    - Handle specific parameters from self.config.get("generation_params", {})

            # Example (conceptual - replace with actual API call):
            # api_payload = {"prompt": text, "model": self.model_name, "context": context, **self.config.get("generation_params", {})}
            # raw_response = self.client.predict(api_payload) # Fictional client call

            # 2. Parse the raw_response from the service
            #    - Extract intents (list), slots (dict), language, etc.
            #    - Map them to the structure expected by this method's return type.

            # Mocked example response:
            mock_intents = [{"intent_name": "example_intent", "confidence": 0.85, "provider_details": {"raw_score": 0.85}}]
            if "weather" in text.lower():
                 mock_intents = [{"intent_name": "get_weather", "confidence": 0.9}]
            mock_slots = {"input_text_length": len(text)}
            if context and context.get("active_slots"):
                mock_slots.update(context["active_slots"])


            return {
                "intents": mock_intents,
                "slots": mock_slots,
                "raw_provider_response": {"data": "mocked raw data from provider"},
                "processed_text": text, # Or text after your provider's preprocessing
                "language": "en-mock" # Mocked language
            }

        # Implement other methods like get_intent, get_slots, process if you want
        # custom behavior beyond the base AdvancedNLPProvider's adaptation.
        # Typically, for AdvancedNLPProvider, these will use process_advanced internally.
    ```

## 3. Configuration (`config/settings.yaml`)

The `config/settings.yaml` file is used to configure and switch between providers.

1.  **Activate Your Provider**:
    *   Set the `active_nlp_provider` key to your provider's module and class name:
        ```yaml
        active_nlp_provider: "my_advanced_provider.MyAdvancedProvider"
        ```

2.  **Add Provider-Specific Configuration**:
    *   Under the `providers:` section, add a new key that **matches the module name** of your provider (e.g., `my_advanced_provider`).
    *   Inside this section, you can specify:
        *   `class` (optional): The class name. If omitted, it's inferred from `active_nlp_provider`.
        *   `api_key_env_var`: **Recommended for API keys.** The name of the environment variable that holds the API key. The loader will read this environment variable and inject the key into the `config` dictionary passed to your provider's `__init__` as `api_key`.
        *   `api_key`: (Less secure) Directly embed the API key. Use with caution.
        *   `default_model`: Specify a default model name or ID.
        *   `timeout`: API call timeout.
        *   `generation_params`: A dictionary for provider-specific generation parameters (e.g., `temperature`, `max_tokens`).
        *   Any other custom settings your provider needs.

    Example for `my_advanced_provider`:
    ```yaml
    # ... other settings ...

    active_nlp_provider: "my_advanced_provider.MyAdvancedProvider"

    providers:
      # ... other provider configurations (dummy_provider, echo_provider, etc.)

      my_advanced_provider: # Key matches module name
        # class: "MyAdvancedProvider" # Optional, can be inferred
        api_key_env_var: "MY_PROVIDER_API_KEY" # Recommended
        # api_key: "direct_api_key_value"    # Alternative (less secure)
        default_model: "model-x-latest"
        timeout: 45
        generation_params:
          temperature: 0.75
          max_new_tokens: 300
        custom_setting: "value_for_my_provider"
    ```
    Your `MyAdvancedProvider.__init__(self, config)` will receive the `my_advanced_provider` dictionary block as its `config` argument. The `config.loader` automatically resolves `api_key_env_var` into an `api_key` entry in this dictionary if the environment variable is set.

## 4. Dependencies

*   Add any external Python libraries required by your provider (e.g., `openai`, `anthropic`, `transformers`, `huggingface_hub`) to the project's `requirements.txt` file.
    ```bash
    pip install openai anthropic # example
    ```

## 5. Testing

*   Create unit tests for your new provider in the `tests/` directory (e.g., `tests/test_my_advanced_provider.py`).
*   Mock external API calls to make tests reliable and avoid actual costs/dependencies during testing.
*   Test various inputs, context handling, and ensure the output structure matches the `AdvancedNLPProvider` interface.
*   Use `python parser/command_parser.py` (after configuring your provider as active) to perform simple end-to-end tests.

By following these steps, you can integrate diverse and powerful NLP services, leveraging features like multi-intent recognition and dialogue context management.
