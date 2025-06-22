# NLP and AI Service Connector Project

This project provides a basic framework for connecting to and switching between multiple external NLP (Natural Language Processing) and AI services. It includes an interface for NLP providers, a configuration mechanism for selecting providers, and a basic command parser.

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
│   ├── base.py               # Abstract base class for NLP providers
│   ├── dummy_provider.py     # Example: Dummy provider with basic logic
│   └── echo_provider.py      # Example: Echo provider
├── parser/                   # Command parsing logic
│   ├── __init__.py
│   └── command_parser.py     # Main command parser class
├── tests/                    # Unit tests
│   └── __init__.py
│   # Test files for providers and parser will go here
└── README.md                 # This file
```

## Features

*   **Pluggable NLP Providers**: Easily add new NLP services by implementing a common interface (`nlp_providers.base.NLPProvider`).
*   **Configuration-based Switching**: Select the active NLP provider through a central configuration file (`config/settings.yaml`).
*   **Basic Command Parsing**: A `CommandParser` class that uses the configured NLP provider to extract intents and slots from text.
*   **Example Providers**: Includes `DummyProvider` and `EchoProvider` as examples and for testing.

## Setup and Installation

1.  **Clone the repository** (if applicable).
2.  **Install dependencies**:
    The main dependency for the core framework is PyYAML.
    ```bash
    pip install pyyaml
    ```
    Specific NLP providers might have their own dependencies. Refer to their documentation or add them to a project `requirements.txt`.

## Configuration

The main configuration is done in `config/settings.yaml`.

*   `active_nlp_provider`: Specifies the module and class name of the NLP provider to use (e.g., `"dummy_provider.DummyProvider"`).
*   Provider-specific settings: Each provider can have its own section in the YAML file, keyed by its module name (e.g., `dummy_provider:`, `echo_provider:`). These settings are passed to the provider's constructor.

See `config/settings.yaml` for an example.

## Integrating New NLP Modules

For detailed instructions on how to add a new NLP provider to this project, please refer to:
[docs/nlp_modules_integration.md](./docs/nlp_modules_integration.md)

## Usage

The `CommandParser` class in `parser/command_parser.py` is the primary entry point for processing text.

```python
from parser.command_parser import CommandParser

# The CommandParser will automatically load the provider configured in settings.yaml
parser = CommandParser()

text_to_parse = "What is the weather in London tomorrow?"
result = parser.parse(text_to_parse)

print(f"Input: {result['text']}")
print(f"Provider: {result.get('provider', 'N/A')}") # Added .get for safety if provider fails to load
print(f"Intent: {result.get('intent', {}).get('intent_name', 'N/A')} (Confidence: {result.get('intent', {}).get('confidence', 0.0)})")
print(f"Slots: {result.get('slots', {})}")
```

You can run `python parser/command_parser.py` for a simple demonstration (it uses the provider configured in `settings.yaml`).
Make sure `dummy_provider.DummyProvider` is implemented and `settings.yaml` points to it for the example to run smoothly.

## Running Examples/Tests

*   **DummyProvider**: `python nlp_providers/dummy_provider.py`
*   **EchoProvider**: `python nlp_providers/echo_provider.py`
*   **CommandParser (with configured provider)**: `python parser/command_parser.py`

(Actual unit tests should be implemented in the `tests/` directory and run with a test runner like `pytest`).

## Future Enhancements

*   Add more sophisticated NLP providers.
*   Implement a similar interface and loading mechanism for AI services.
*   Develop more comprehensive unit and integration tests.
*   Add asynchronous support for NLP provider calls.
*   More robust error handling and logging.