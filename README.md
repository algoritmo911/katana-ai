# katana-ai

## Autosuggest Agent

This project includes a smart autosuggest agent that provides command suggestions to the user in a Telegram bot. The agent is designed to be extensible, with support for different suggestion modes (static, semantic, and LLM-based).

### Architecture

The autosuggest agent is built with a modular architecture:

-   `katana/agents/suggest_agent.py`: The core of the agent, responsible for generating suggestions.
-   `katana/telegram/handlers/telegram_handler.py`: The Telegram bot handler, which integrates with the suggest agent.
-   `katana/tests/agents/test_suggest_agent.py`: Unit tests for the suggest agent.

### How it works

The `SuggestAgent` class in `suggest_agent.py` provides three modes for generating suggestions:

-   **Static**: This mode uses a predefined dictionary of keywords and corresponding commands to provide suggestions. It's fast and simple, but not very flexible.
-   **Semantic**: This mode is a placeholder for a more advanced NLP-based suggestion engine. It could use techniques like word embeddings and cosine similarity to find the most relevant commands.
-   **LLM**: This mode is a placeholder for a large language model-based suggestion engine. It would use a powerful LLM like GPT-3 to generate suggestions based on the user's input and the conversation history.

The `TelegramHandler` class in `telegram_handler.py` uses the `SuggestAgent` to provide suggestions to the user as inline keyboard buttons. When the user clicks on a button, the corresponding command is sent to the bot.

### How to extend

The autosuggest agent can be extended in several ways:

-   **Add more commands to the static dictionary**: This is the easiest way to improve the suggestions.
-   **Implement the semantic suggestion mode**: This would require a good understanding of NLP techniques.
-   **Implement the LLM suggestion mode**: This would require access to a powerful LLM and a good understanding of prompt engineering.
-   **Add support for more suggestion modes**: The `SuggestAgent` is designed to be extensible, so it's easy to add support for new suggestion modes.
