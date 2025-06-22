# Katana Bot Project

Katana Bot is a Telegram bot designed for various automated tasks and interactions. It features a flexible command processing system and is now enhanced with AI capabilities and asynchronous operations for improved performance.

## Features

-   **Command Processing:** Handles JSON-based commands sent via Telegram.
-   **Modular Design:** Organizes commands and functionalities into modules.
-   **AI Integration:**
    -   Supports interactions with multiple AI providers:
        -   OpenAI (e.g., GPT models for text generation)
        -   Anthropic (e.g., Claude models for text generation)
        -   HuggingFace (e.g., various models for text generation and text-to-image tasks)
    -   AI requests are managed via the `ai_request` command type.
-   **Asynchronous Architecture:**
    -   Utilizes `asyncio` and `async_telebot` for non-blocking operations, ensuring the bot remains responsive.
    -   AI provider interactions are performed asynchronously.
-   **Sandbox Environment:** Includes a `sandbox/` directory for experimenting with new features, AI models, and prototyping ideas without affecting the main bot.
-   **Logging:** Basic event logging to the console.

## Project Structure

```
├── bot/
│   ├── ai_providers/       # Modules for different AI SDKs (OpenAI, Anthropic, HuggingFace)
│   │   ├── __init__.py
│   │   ├── anthropic.py
│   │   ├── huggingface.py
│   │   └── openai.py
│   ├── commands/           # Directory for storing received command JSON files
│   │   ├── __init__.py
│   ├── katana_bot.py       # Main bot logic, command handling, async operations
│   └── test_bot.py         # (Placeholder/Existing) Bot tests
├── legacy_ui/              # Legacy UI components
├── requirements.txt        # Python dependencies
├── sandbox/                # Sandbox for experiments and prototypes
│   ├── __init__.py
│   ├── README.md           # Guide for using the sandbox
│   └── example_ai_test.py  # Example script for testing AI providers
├── ui/                     # Current UI components
└── README.md               # This file
```

## Setup and Running

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd katana-bot-project
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    You need to provide API keys for Telegram and any AI services you intend to use. Create a `.env` file in the project root or set environment variables directly:
    ```env
    KATANA_TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    OPENAI_API_KEY="YOUR_OPENAI_API_KEY"          # Optional, for OpenAI features
    ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY"    # Optional, for Anthropic features
    HUGGINGFACE_API_TOKEN="YOUR_HUGGINGFACE_API_TOKEN" # Optional, for HuggingFace features
    ```
    The `python-dotenv` library (included in `requirements.txt`) will automatically load variables from a `.env` file if present when scripts like `sandbox/example_ai_test.py` are run. The main bot script `katana_bot.py` also loads these at startup using `os.getenv`.

5.  **Run the bot:**
    ```bash
    python bot/katana_bot.py
    ```

## Using AI Features

Send a JSON command to the bot with `type` set to `ai_request`.

**Required `args` for `ai_request`:**
-   `provider`: Specifies the AI provider. Supported values: `"openai"`, `"anthropic"`, `"huggingface"`.
-   `prompt`: The text prompt for the AI.

**Optional `args`:**
-   `model`: Specify a particular model for the chosen provider. Defaults are used if not provided (e.g., "gpt-3.5-turbo" for OpenAI).
-   `task` (for HuggingFace):
    -   If `task` is `"text-to-image"`, the bot will attempt to generate an image.
    -   Otherwise, text generation is assumed.

**Example JSON command for OpenAI text generation:**
```json
{
  "type": "ai_request",
  "module": "ai_general",
  "args": {
    "provider": "openai",
    "prompt": "What is the weather like today?",
    "model": "gpt-4"
  },
  "id": "user123_openai_query_1"
}
```

**Example JSON command for HuggingFace text-to-image:**
```json
{
  "type": "ai_request",
  "module": "ai_hf_image",
  "args": {
    "provider": "huggingface",
    "task": "text-to-image",
    "prompt": "A cat wearing a wizard hat",
    "model": "stabilityai/stable-diffusion-2"
  },
  "id": "user123_hf_image_1"
}
```

## Development

-   **Sandbox:** Use the `sandbox/` directory to test new features. Run `sandbox/example_ai_test.py` to verify AI provider setup.
-   **Testing:** (Further test development needed) Add unit and integration tests in `bot/test_bot.py` and potentially new test files for AI providers.

## Contributing

(Add contribution guidelines if applicable)

---

This README provides a basic overview. Further details on specific modules or functionalities can be found within their respective directories or code comments.
