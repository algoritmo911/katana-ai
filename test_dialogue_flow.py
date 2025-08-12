import os
import json

# --- Setup Instructions ---
# 1. Make sure you have an OpenAI API key set in your environment variables.
#    export OPENAI_API_KEY='your_key_here'
#
# 2. This test uses SIMULATED LLM calls by default.
#    To use the REAL OpenAI API, change USE_REAL_LLM to True below.
USE_REAL_LLM = False

# --- Mocking ---
# We need to patch the llm_handler functions if we are not using the real LLM.
if not USE_REAL_LLM:
    from unittest.mock import patch

    # This is a simplified simulation of what a real LLM might return.
    def mock_llm_slot_filler(text, tool_schemas):
        print(f"\n[MOCK LLM] Received for slot filling: '{text}'")
        text = text.lower()
        if "отчет" in text:
            if "прометей" in text:
                return {"tool_name": "get_report", "filled_parameters": {"project_name": "Прометей"}}
            else:
                # Simulates asking for a project
                return {"tool_name": "get_report", "filled_parameters": {}}
        elif "статус" in text or "система" in text:
            return {"tool_name": "get_system_status", "filled_parameters": {}}
        print("[MOCK LLM] No tool match found.")
        return None

    def mock_llm_clarification_generator(missing_param_name, param_schema):
        print(f"[MOCK LLM] Received for clarification: missing '{missing_param_name}'")
        if missing_param_name == "project_name":
            return "Конечно. Уточните, по какому проекту?"
        if missing_param_name == "date_range":
            return "За какой период времени?"
        return f"Уточните, пожалуйста, '{missing_param_name}'."

    # Apply the patches
    patch_slot_filler = patch('nlp.llm_handler.call_llm_for_slot_filling', side_effect=mock_llm_slot_filler)
    patch_clarification = patch('nlp.llm_handler.call_llm_for_clarification_question', side_effect=mock_llm_clarification_generator)

    patch_slot_filler.start()
    patch_clarification.start()

# Now we can import the engine. It will be initialized with the mocked functions if applicable.
from nlp.main import process_message

def run_test_dialogue():
    """
    Simulates a multi-turn conversation to test the full NLP pipeline.
    """
    print("--- Starting Dialogue Flow Test ---")

    USER_ID = "test_user_123"

    # --- Test Case 1: Multi-turn dialogue for slot filling ---
    print("\n--- SCENARIO 1: Successful multi-turn dialogue ---")

    # 1. User asks for a report without specifying the project
    print("\n[USER] Покажи мне отчет.")
    response = process_message(USER_ID, "Покажи мне отчет.")
    print(f"[BOT] {response}")

    # Assert: Bot should ask for the project name
    assert response['action'] == 'reply'
    assert "по какому проекту" in response['text']
    print("✅   Test Passed: Bot correctly asked for the missing project name.")

    # 2. User provides the project name
    print("\n[USER] Прометей")
    response = process_message(USER_ID, "Прометей")
    print(f"[BOT] {response}")

    # Assert: Bot should now have all required slots and confirm execution
    assert response['action'] == 'reply'
    assert "все данные собраны" in response['text']
    assert "get_report" in response['text']
    assert '"project_name": "Прометей"' in response['text']
    print("✅   Test Passed: Bot correctly filled the slot and confirmed execution.")

    # --- Test Case 2: Embedding classifier direct hit ---
    print("\n--- SCENARIO 2: Embedding classifier finds direct match ---")

    # User asks for system status, which should be a close match to a tool description
    print("\n[USER] как там система себя чувствует?")
    response = process_message(USER_ID, "как там система себя чувствует?")
    print(f"[BOT] {response}")

    assert response['action'] == 'reply'
    assert "get_system_status" in response['text']
    assert "все данные собраны" in response['text'] # Since this tool has no params
    print("✅   Test Passed: Embedding classifier correctly identified 'get_system_status'.")

    # --- Test Case 3: Hard-coded command ---
    print("\n--- SCENARIO 3: Hard-coded command is triggered ---")

    print("\n[USER] /status")
    response = process_message(USER_ID, "/status")
    print(f"[BOT] {response}")

    assert response['action'] == 'reply'
    assert "get_system_status" in response['text']
    print("✅   Test Passed: Hard-coded command '/status' correctly mapped to 'get_system_status'.")


    print("\n--- Dialogue Flow Test Finished Successfully! ---")

if __name__ == "__main__":
    # If not using real LLM, we don't need to check for the key.
    if USE_REAL_LLM and not os.environ.get("OPENAI_API_KEY"):
        print("\nERROR: To run with a real LLM, please set the OPENAI_API_KEY environment variable.")
        print("export OPENAI_API_KEY='your_key_here'\n")
    else:
        run_test_dialogue()

    # Stop patches if they were started
    if not USE_REAL_LLM:
        patch_slot_filler.stop()
        patch_clarification.stop()
