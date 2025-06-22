import os

# Environment variable to choose NLP engine
# Set USE_LLM_NLP=true in your environment to simulate using an LLM
USE_LLM_NLP = os.environ.get('USE_LLM_NLP', 'false').lower() == 'true'

def basic_interpret(text: str) -> str | None:
    """Basic keyword-based text interpretation."""
    text = text.lower()
    # Order can matter if keywords overlap. More specific checks can go first.
    if "красивый аптайм" in text or "аптайм красиво" in text or ("аптайм" in text and "подробно" in text):
        return "uptime -p"
    if "место" in text or "диск" in text:
        return "df -h"
    if "работает" in text or "аптайм" in text: # General uptime, will be caught if more specific above isn't.
        return "uptime"
    if "память" in text or "оперативка" in text or "сколько памяти" in text:
        return "free -m"
    if "кто я" in text or "пользователь" in text or "юзер" in text: # "юзер" is a common transliteration
        return "whoami"
    if "дата" in text or "время" in text or "какое сегодня число" in text:
        return "date"
    if "загрузка" in text or "cpu" in text or "процессор" in text:
        return "top -n1 | head -5"
    if "папки" in text or "файлы" in text or "список" in text:
        return "ls -al"
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
