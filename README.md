# NLP and AI Service Connector Project

This project provides a flexible framework for connecting to, configuring, and switching between multiple external NLP (Natural Language Processing) services. It supports basic and advanced NLP providers, context management for dialogues, and configurable fallback mechanisms.

## Project Structure

```
.
├── config/                   # Configuration files
│   ├── __init__.py
│   ├── loader.py             # Loads configuration and active providers
│   └── settings.yaml         # Main configuration file (YAML format)
├── docs/                     # Documentation
│   ├── __init__.py
│   └── nlp_modules_integration.md # Guide for adding new NLP modules
├── nlp_providers/            # NLP provider implementations
│   ├── __init__.py
│   ├── base.py               # Abstract base class for NLP providers (NLPProvider)
│   ├── advanced_base.py      # Abstract base class for advanced NLP providers (AdvancedNLPProvider)
│   ├── dummy_provider.py     # Example: Basic provider with keyword/regex logic
│   ├── echo_provider.py      # Example: Echoes input
│   └── example_openai_provider.py # Example: Conceptual advanced provider (mocked OpenAI)
├── parser/                   # Command parsing logic
│   ├── __init__.py
│   └── command_parser.py     # Main command parser class, handles context and advanced providers
├── tests/                    # Unit tests
│   └── __init__.py
│   # Test files for providers, parser, and config_loader
└── README.md                 # This file
```

## Key Features

*   **Pluggable NLP Providers**:
    *   Supports basic (`NLPProvider`) and advanced (`AdvancedNLPProvider`) interfaces.
    *   Advanced providers can handle multi-intent recognition, dialogue context, and richer response formats.
*   **Flexible Configuration (`config/settings.yaml`)**:
    *   Easily switch between different NLP providers (e.g., OpenAI, Anthropic, HuggingFace).
    *   Manage provider-specific settings, API keys (via environment variables), model names, and generation parameters.
*   **Upgraded Command Parser (`parser/command_parser.py`)**:
    *   Works with both basic and advanced NLP providers.
    *   Manages basic dialogue context (can be extended for multi-step dialogues).
    *   Provides configurable fallback responses for unrecognized commands.
    *   Conceptual integration point for `katana_agent_bridge`.
*   **Example Providers**:
    *   `DummyProvider` and `EchoProvider` (basic).
    *   `ExampleOpenAIProvider` (conceptual advanced provider with mocked API calls).
*   **Comprehensive Documentation**:
    *   Detailed guide for integrating new NLP modules (`docs/nlp_modules_integration.md`).

## Setup and Installation

1.  **Clone the repository** (if applicable).
2.  **Install dependencies**:
    The main dependency for the core framework is PyYAML.
    ```bash
    pip install pyyaml
    ```
    Specific NLP providers (especially advanced ones using external SDKs like `openai`, `anthropic`, `transformers`) will have their own dependencies. List them in a project `requirements.txt` and install as needed.
    ```bash
    # Example: pip install openai anthropic transformers huggingface_hub
    ```
3.  **Environment Variables**: For providers requiring API keys (e.g., OpenAI, Anthropic, private HuggingFace models), set the corresponding environment variables as specified in `config/settings.yaml` (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `HF_HUB_TOKEN`).

## Configuration

The main configuration is in `config/settings.yaml`.

*   `active_nlp_provider`: Specifies the module and class name of the NLP provider to use (e.g., `"dummy_provider.DummyProvider"` or `"example_openai_provider.ExampleOpenAIProvider"`). The module name part (e.g., `example_openai_provider`) must also be a key under the `providers` section.
*   `providers`: A dictionary where each key is a provider's module name. The value is another dictionary containing:
    *   `class` (optional): The class name within the module. Inferred if not present.
    *   `api_key_env_var`: Recommended. The name of the environment variable holding the API key.
    *   `api_key`: Alternative (less secure) to directly embed the key.
    *   `default_model`: Default model for the provider.
    *   `timeout`: API call timeout.
    *   `generation_params`: Provider-specific parameters for text generation.
    *   Other custom settings.

Refer to `config/settings.yaml` for detailed examples. The `config/loader.py` handles loading this configuration and instantiating the active provider.

## Integrating New NLP Modules

For detailed instructions on adding new basic or advanced NLP providers, configuring them, and handling dependencies, please see:
**[docs/nlp_modules_integration.md](./docs/nlp_modules_integration.md)**

## Usage

The `CommandParser` class in `parser/command_parser.py` is the primary entry point.

```python
from parser.command_parser import CommandParser
import os

# Example: Set an API key for a provider if it's configured to use one from env
# os.environ["OPENAI_API_KEY"] = "your_actual_openai_api_key_or_a_dummy_one_for_mocked_provider"

# Initialize the parser (loads provider based on settings.yaml)
# You can also pass an initial dialogue_context
parser = CommandParser(dialogue_context={"user_id": "test_user"})

# Example text and context for parsing
text_to_parse = "What's the weather in London and book a flight to Paris for tomorrow?"
# Context can be passed per parse call to override/augment the parser's internal context
current_call_context = {"location_hint": "UK"}

result = parser.parse(text_to_parse, context_override=current_call_context)

print(f"Input Text: {result.get('text')}")
print(f"Provider Used: {result.get('provider')}")

print("\nIdentified Intents:")
for intent_info in result.get('intents', []):
    print(f"  - Name: {intent_info.get('intent_name')}, Confidence: {intent_info.get('confidence')}")
    if intent_info.get('provider_details'):
        print(f"    Provider Details: {intent_info.get('provider_details')}")

print(f"\nExtracted Slots: {result.get('slots')}")

if result.get('fallback_response'):
    print(f"\nFallback Response: {result.get('fallback_response')}")

if result.get('language'):
    print(f"\nDetected Language: {result.get('language')}")

# The parser's internal dialogue context is updated after each parse call
print(f"\nParser's Updated Dialogue Context: {parser.dialogue_context}")

# Conceptual: Prepare for Katana Agent Bridge
# katana_action = parser._prepare_for_katana_bridge(result) # This method is conceptual
# print(f"\nConceptual Katana Action: {katana_action}")
```

Run `python parser/command_parser.py` for a demonstration. This script uses the provider configured in `settings.yaml`. Ensure any required environment variables for the active provider are set.

## Running Examples & Tests

*   **Provider Examples**:
    *   `python nlp_providers/dummy_provider.py`
    *   `python nlp_providers/echo_provider.py`
    *   `python nlp_providers/example_openai_provider.py` (ensure `OPENAI_API_KEY` is set, even to a dummy value for the mocked provider).
*   **CommandParser Demo**: `python parser/command_parser.py`
*   **Unit Tests**:
    Run tests using `unittest` from the project root:
    ```bash
    python -m unittest discover -s tests -p "test_*.py"
    ```
    (More comprehensive tests for advanced scenarios and specific provider integrations should be added).

## Future Enhancements

*   Implement fully functional advanced NLP providers for services like OpenAI, Anthropic, HuggingFace (local and API).
*   Develop a more sophisticated `DialogueManager` for robust multi-step conversation handling.
*   Flesh out the `katana_agent_bridge` integration.
*   Add comprehensive unit and integration tests for various complex scenarios.
*   Introduce asynchronous operations for NLP provider calls to improve performance.
*   Enhance logging and error reporting throughout the framework.