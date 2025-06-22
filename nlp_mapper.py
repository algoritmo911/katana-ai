import os

# Environment variable to choose NLP engine
# Set USE_LLM_NLP=true in your environment to simulate using an LLM
USE_LLM_NLP = os.environ.get('USE_LLM_NLP', 'false').lower() == 'true'

def basic_interpret(text: str) -> str | None:
    """Basic keyword-based text interpretation."""
    original_text = text # Keep original for potential raw command execution
    text = text.lower()

    # Handle /run <command> syntax
    if text.startswith("/run "):
        command_part = original_text[5:].strip() # Extract command after "/run "
        # If the extracted command is simple and known, map it.
        # Otherwise, return the raw command_part to be executed directly.
        # This allows for flexibility, e.g., /run custom_script.sh arg1
        if command_part.lower() == "uptime":
            return "uptime"
        if command_part.lower() == "df -h":
            return "df -h"
        if command_part.lower() == "ls -al":
            return "ls -al"
        # Add more known /run commands if needed, or just return command_part
        if command_part: # Ensure it's not empty
            return command_part # Execute arbitrary command
        else:
            return None # Or some error/help message for "/run " with no command

    # Existing keyword-based interpretation
    if "место" in text or "диск" in text:
        return "df -h"
    if "работает" in text or "аптайм" in text:
        return "uptime"
    if "загрузка" in text or "cpu" in text or "процессор" in text: # Added "процессор"
        return "top -n1 | head -5"
    if "папки" in text or "файлы" in text or "список" in text: # Added "список"
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
