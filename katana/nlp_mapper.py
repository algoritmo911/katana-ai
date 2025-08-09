import os

# Environment variable to choose NLP engine
# Set USE_LLM_NLP=true in your environment to simulate using an LLM
USE_LLM_NLP = os.environ.get('USE_LLM_NLP', 'false').lower() == 'true'

# --- NLP Command Mapping ---
COMMAND_SYNONYMS = {
    "greet": ["привет", "здорово", "добрый день", "здравствуй", "хай", "хелло"],
    "disk_space": ["место", "диск", "сколько места", "объем диска"],
    "uptime": ["работает", "аптайм", "как долго работает", "время работы"],
    "cpu_load": ["загрузка", "cpu", "процессор", "цпу", "нагрузка на процессор"],
    "list_files": ["папки", "файлы", "список", "содержимое", "что в папке", "что в этой папке лежит?"],
    "weather": ["погода", "прогноз погоды", "какая погода"],
    "joke": ["анекдот", "шутка", "расскажи анекдот", "пошути", "хочу шутку"]
}

COMMAND_ACTIONS = {
    "greet": lambda: "Привет! Как я могу помочь?", # Placeholder action for greeting
    "disk_space": "df -h",
    "uptime": "uptime",
    "cpu_load": "top -n1 | head -5",
    "list_files": "ls -al",
    "weather": "get_weather", # Special keyword for API call
    "joke": "get_joke"      # Special keyword for API call
}

def basic_interpret(text: str) -> str | None:
    """Basic keyword-based text interpretation with synonym support."""
    text_lower = text.lower()
    for command_key, synonyms in COMMAND_SYNONYMS.items():
        for synonym in synonyms:
            if synonym in text_lower:
                action = COMMAND_ACTIONS.get(command_key)
                if callable(action): # For dynamic actions like greeting
                    return action()
                return action
    return None

def llm_interpret(text: str) -> str | None:
    """
    Placeholder for a more advanced LLM-based interpreter.
    This function would call out to OpenAI, Transformers, etc.
    """
    # In a real scenario, you would have:
    # client = OpenAIClient() / load_transformer_model()
    # response = client.get_command(text)
    # return response.command if response.is_valid else None
    print(f"[NLP_MAPPER] LLM interpretation called for: '{text}' (Not implemented, returning None)")
    if "example llm command for uptime" in text.lower(): # Dummy example for testing
        return "uptime"
    return None

def get_interpreter():
    """
    Returns the appropriate NLP interpretation function based on configuration.
    Reads USE_LLM_NLP environment variable dynamically.
    """
    use_llm_dynamically = os.environ.get('USE_LLM_NLP', 'false').lower() == 'true'
    if use_llm_dynamically:
        print("[NLP_MAPPER] Using LLM-based interpreter (dynamically checked).")
        return llm_interpret
    else:
        print("[NLP_MAPPER] Using basic keyword-based interpreter (dynamically checked).")
        return basic_interpret

# Default interpreter to be imported by other modules
# This will be set once at import time based on the initial environment.
# For dynamic switching in tests or long-running apps, call get_interpreter() directly if needed,
# or ensure the main application re-imports or calls a re-initialization function.
# For the bot's case, it imports `interpret` once, so its behavior is fixed at startup.
interpret = get_interpreter()
