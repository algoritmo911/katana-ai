import os

# Environment variable to choose NLP engine
# Set USE_LLM_NLP=true in your environment to simulate using an LLM
USE_LLM_NLP = os.environ.get("USE_LLM_NLP", "false").lower() == "true"


def basic_interpret(text: str) -> str | None:
    """Basic keyword-based text interpretation."""
    text = text.lower()
    # Existing commands
    if "место" in text or "диск" in text:
        return '{"type": "exec", "module": "system", "args": {"command": "df -h"}, "id": "nlp-disk"}'
    if "работает" in text or "аптайм" in text:
        return '{"type": "exec", "module": "system", "args": {"command": "uptime"}, "id": "nlp-uptime"}'
    if "загрузка" in text or "cpu" in text or "процессор" in text:
        return '{"type": "exec", "module": "system", "args": {"command": "top -n1 | head -5"}, "id": "nlp-cpu"}'
    if "папки" in text or "файлы" in text or "список" in text:
        return '{"type": "exec", "module": "system", "args": {"command": "ls -al"}, "id": "nlp-ls"}'
    if (
        "память" in text
        or "памяти" in text
        or "ram" in text
        or "оперативка" in text
        or "оперативки" in text
    ):
        return '{"type": "exec", "module": "system", "args": {"command": "free -h"}, "id": "nlp-ram"}'
    if (
        "инфо о системе" in text
        or "ядро" in text
        or "версия ос" in text
        or "система инфо" in text
    ):
        return '{"type": "exec", "module": "system", "args": {"command": "uname -a"}, "id": "nlp-sysinfo"}'
    if "сетевые подключения" in text or "порты" in text or "соединения" in text:
        return '{"type": "exec", "module": "system", "args": {"command": "ss -tulnp"}, "id": "nlp-net"}'
    if "пинг google" in text or "связь с google" in text:
        return '{"type": "exec", "module": "system", "args": {"command": "ping -c 3 google.com"}, "id": "nlp-ping"}'

    # New command_type keywords
    if "повтори" in text:
        return '{"type": "repeat", "module": "core", "args": {}, "id": "nlp-repeat"}'
    if "стоп" in text or "хватит" in text:
        return '{"type": "stop", "module": "core", "args": {}, "id": "nlp-stop"}'
    if "инфо" in text or "расскажи" in text:
        # This is a bit generic, might need more specific keywords
        return '{"type": "info", "module": "general", "args": {"text": "This is an informational message."}, "id": "nlp-info"}'

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
    print(
        f"[NLP_MAPPER] LLM interpretation called for: '{text}' (Not implemented, returning None)"
    )
    if "example llm command for uptime" in text.lower():  # Dummy example for testing
        return "uptime"
    return None


def get_interpreter():
    """
    Returns the appropriate NLP interpretation function based on configuration.
    Reads USE_LLM_NLP environment variable dynamically.
    """
    use_llm_dynamically = os.environ.get("USE_LLM_NLP", "false").lower() == "true"
    if use_llm_dynamically:
        print("[NLP_MAPPER] Using LLM-based interpreter (dynamically checked).")
        return llm_interpret
    else:
        print(
            "[NLP_MAPPER] Using basic keyword-based interpreter (dynamically checked)."
        )
        return basic_interpret


# Default interpreter to be imported by other modules
# This will be set once at import time based on the initial environment.
# For dynamic switching in tests or long-running apps, call get_interpreter() directly if needed,
# or ensure the main application re-imports or calls a re-initialization function.
# For the bot's case, it imports `interpret` once, so its behavior is fixed at startup.
interpret = get_interpreter()
