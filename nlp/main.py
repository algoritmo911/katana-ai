import json
from typing import Dict, Any

from nlp.tool_registry import ToolRegistry
from nlp.intent_classifier import IntentClassifier
from nlp.dialogue_manager import DialogueManager
from nlp.llm_handler import call_llm_for_slot_filling

class NlpEngine:
    """
    The main "Synapse" NLP engine.
    This class initializes and holds all the necessary components for processing messages.
    """
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.intent_classifier = IntentClassifier(self.tool_registry)
        self.dialogue_manager = DialogueManager(self.tool_registry)

    def process_message(self, user_id: str, text: str) -> Dict[str, Any]:
        """
        Processes an incoming text message from a user and returns an action.

        Args:
            user_id: The unique identifier for the user.
            text: The user's message.

        Returns:
            A dictionary representing the action to take, e.g.:
            - {'action': 'reply', 'text': '...'}
            - {'action': 'execute', 'tool': '...', 'params': {...}}
            - {'action': 'do_nothing'}
        """
        # First, check if the user is in the middle of a conversation
        dialogue_response = self.dialogue_manager.handle_user_response(user_id, text)
        if dialogue_response:
            # The dialogue manager handled it (e.g., asked another question or is ready to execute)
            # This part needs refinement to distinguish between another question and execution
            return {'action': 'reply', 'text': dialogue_response}

        # If not in a dialogue, start the classification cascade
        intent = self.intent_classifier.classify(text)
        source = intent.get('source', 'unknown')

        if intent['type'] == 'tool':
            tool_name = intent['name']
            # For now, assume no parameters were extracted yet. Pass to dialogue manager.
            # A more advanced version might extract simple params here.
            response = self.dialogue_manager.start_slot_filling(user_id, tool_name, {})
            return {'action': 'reply', 'text': f"[Source: {source}]\n{response}"}

        elif intent['type'] == 'escalate_llm':
            # Escalate to the LLM for full tool selection and slot filling
            tool_schemas = self.tool_registry.get_tool_schemas_for_llm()
            llm_result = call_llm_for_slot_filling(text, tool_schemas)

            if not llm_result:
                return {'action': 'reply', 'text': "🤖 Не понял команду. Попробуй переформулировать."}

            tool_name = llm_result['tool_name']
            params = llm_result['filled_parameters']

            # Now, pass this to the dialogue manager to check for missing slots
            response = self.dialogue_manager.start_slot_filling(user_id, tool_name, params)
            return {'action': 'reply', 'text': f"[Source: llm_slot_filler]\n{response}"}

        return {'action': 'do_nothing'}


# Create a global instance of the engine
# This makes it easy to import and use in the bot.
SYNAPSE_ENGINE = NlpEngine()

def process_message(user_id: str, text: str) -> Dict[str, Any]:
    """Public-facing function to be called by the bot."""
    return SYNAPSE_ENGINE.process_message(user_id, text)
