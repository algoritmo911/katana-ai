import json
from typing import List, Dict, Any, Optional

# This is a placeholder for a real LLM client, e.g., from openai
# from openai import OpenAI
# client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def call_llm_for_slot_filling(text: str, tool_schemas: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    (Placeholder) Calls a Large Language Model to perform tool selection and slot-filling.

    In a real implementation, this function would:
    1. Construct a detailed system prompt explaining the task.
    2. Format the user's text and the available tool schemas.
    3. Send the request to the LLM API (e.g., OpenAI's chat completions).
    4. Specify a JSON response format.
    5. Parse the LLM's JSON response and return it.

    Args:
        text: The user's input message.
        tool_schemas: A list of schemas for the available tools.

    Returns:
        A dictionary with "tool_name" and "filled_parameters", or None on failure.
    """
    print(f"--- LLM Call (Simulation) for Slot-Filling ---")
    print(f"User Text: '{text}'")
    print(f"Tool Schemas: {json.dumps(tool_schemas, indent=2)}")

    # --- SIMULATION LOGIC ---
    # This is a hardcoded simulation for the example dialogue.
    # A real implementation would parse the LLM's response.
    if "прометей" in text.lower() and "коммиты" in text.lower():
        return {
            "tool_name": "find_commits",
            "filled_parameters": {
                "project_name": "Прометей",
                "date_range": "last_week" # Assuming from "за последнюю неделю"
            }
        }
    elif "отчет" in text.lower() and "прометей" in text.lower():
         return {
            "tool_name": "get_report",
            "filled_parameters": {
                "project_name": "Прометей"
                # "date_range" is missing
            }
        }
    elif "отчет" in text.lower():
         return {
            "tool_name": "get_report",
            "filled_parameters": {
                # "project_name" is missing
            }
        }

    print("--- LLM Simulation: No specific tool matched. ---")
    return None


def call_llm_for_clarification_question(missing_param_name: str, param_schema: Dict[str, Any]) -> str:
    """
    (Placeholder) Calls an LLM to generate a user-friendly question to ask for a missing parameter.

    Args:
        missing_param_name: The name of the parameter that is missing.
        param_schema: The JSON schema of the missing parameter.

    Returns:
        A natural language question to ask the user.
    """
    print(f"--- LLM Call (Simulation) for Clarification Question ---")
    print(f"Missing Parameter: '{missing_param_name}'")

    # --- SIMULATION LOGIC ---
    description = param_schema.get('description', '')

    if missing_param_name == "project_name":
        return "Конечно. Уточните, по какому проекту?"
    if missing_param_name == "date_range":
        return "За какой период времени?"

    # A generic fallback
    if description:
        return f"Уточните, пожалуйста, значение для '{missing_param_name}' ({description})."
    else:
        return f"Уточните, пожалуйста, значение для '{missing_param_name}'."
