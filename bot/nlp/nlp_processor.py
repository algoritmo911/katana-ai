import openai
import os
from functools import lru_cache
from pathlib import Path

# --- Constants ---
DEFAULT_MODEL = "gpt-4-turbo-preview"
SYSTEM_PROMPT_FILE = Path(__file__).parent / "system_prompt.md"

class NLPError(Exception):
    """Custom exception for NLP processing errors."""
    pass

class NLPProcessor:
    """
    Handles interaction with the OpenAI API for NLP tasks.
    It is configured via environment variables.
    """
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model_name = os.getenv("OPENAI_MODEL_NAME", DEFAULT_MODEL)
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Loads the system prompt from the specified file."""
        try:
            with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            # Fallback if the file is missing
            return "You are a helpful assistant."
        except Exception as e:
            print(f"Error loading system prompt: {e}")
            return "You are a helpful assistant."

    @lru_cache(maxsize=128)
    def process_text(self, text: str, dialogue_history_json: str = "[]") -> dict:
        """
        Processes the user's text using the configured OpenAI model.
        Uses lru_cache to cache results for identical inputs.

        :param text: The user's input text.
        :param dialogue_history_json: A JSON string representing the conversation history.
        :return: A dictionary containing the structured NLP result.
        """
        # This is a simplified placeholder for the actual complex call to the LLM.
        # In a real scenario, this would involve constructing a detailed prompt
        # with few-shot examples, tools, and the dialogue history.

        # For testing and demonstration, we'll return a mock structure.
        # This simulates the kind of output the real LLM would be prompted to provide.
        if "weather" in text.lower() and "paris" in text.lower():
            return {
                "intent": "get_weather",
                "entities": [{"text": "Paris", "type": "city"}],
                "dialogue_state": "new_request"
            }
        elif "weather" in text.lower():
             return {
                "intent": "get_weather",
                "entities": [],
                "dialogue_state": "new_request"
            }
        elif "time" in text.lower():
            return {
                "intent": "get_time",
                "entities": [],
                "dialogue_state": "new_request"
            }

        # Default fallback response from the mock
        return {
            "intent": "fallback_general",
            "entities": [],
            "dialogue_state": "new_request"
        }
