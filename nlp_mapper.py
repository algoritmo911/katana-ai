import os

# Environment variable to choose NLP engine
# Set USE_LLM_NLP=true in your environment to simulate using an LLM
USE_LLM_NLP = os.environ.get('USE_LLM_NLP', 'false').lower() == 'true'

def basic_interpret(text: str) -> str | None:
    """
    More structured keyword-based text interpretation.
    Maps keywords to commands for better scalability and maintainability.
    """
    original_text = text
    text = text.lower()

    # Command mapping
    # Maps a command to a list of keywords.
    COMMANDS = {
        "df -h": ["место", "диск", "filesystem"],
        "uptime": ["работает", "аптайм", "uptime"],
        "top -n1 | head -5": ["загрузка", "cpu", "процессор", "load"],
        "ls -al": ["папки", "файлы", "список", "ls", "files", "list"],
    }

    # Handle /run <command> syntax for direct execution
    if text.startswith("/run "):
        command_part = original_text[5:].strip()
        if not command_part:
            return None  # No command provided after /run

        # Normalize known commands
        for command in COMMANDS.keys():
            if command_part.lower() == command:
                return command

        # Fallback to executing the arbitrary command
        return command_part

    # NLP-like keyword matching
    for command, keywords in COMMANDS.items():
        if any(keyword in text for keyword in keywords):
            return command

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
