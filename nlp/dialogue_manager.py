import json
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field

from nlp.tool_registry import ToolRegistry, ToolContract
from nlp.llm_handler import call_llm_for_clarification_question

class DialogueState(BaseModel):
    """
    Represents the state of a conversation with a single user, particularly when
    the system is trying to fill slots for a specific tool.
    """
    user_id: str
    active_tool_name: str
    filled_slots: Dict[str, Any] = Field(default_factory=dict)
    missing_slot_name: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class DialogueManager:
    """
    Manages the dialogue states for all users. It keeps track of ongoing
    conversations where the system is waiting for more information.
    """
    def __init__(self, tool_registry: ToolRegistry):
        # Using a simple in-memory dictionary. For production, this could be Redis.
        self._states: Dict[str, DialogueState] = {}
        self.tool_registry = tool_registry

    def get_state(self, user_id: str) -> Optional[DialogueState]:
        """Retrieves the dialogue state for a given user."""
        return self._states.get(user_id)

    def clear_state(self, user_id: str):
        """Clears the dialogue state for a user, ending the conversation."""
        if user_id in self._states:
            del self._states[user_id]

    def start_slot_filling(self, user_id: str, tool_name: str, filled_parameters: Dict[str, Any]) -> str:
        """
        Starts or continues the slot-filling process for a user and a chosen tool.
        It checks for missing required parameters and generates a clarification question if needed.

        Returns:
            A message to be sent back to the user. This can be a clarification
            question or a confirmation that the tool will be executed.
        """
        tool_contract = self.tool_registry.get_tool(tool_name)
        if not tool_contract:
            return "Ошибка: я попытался использовать инструмент, который не существует."

        # Get the schema for the tool's parameters
        param_schema = tool_contract.parameters.model_json_schema()
        required_params = param_schema.get('required', [])

        # Find the first missing required parameter
        missing_param = None
        for param_name in required_params:
            if param_name not in filled_parameters:
                missing_param = param_name
                break

        if missing_param:
            # A required parameter is missing, create a dialogue state
            state = DialogueState(
                user_id=user_id,
                active_tool_name=tool_name,
                filled_slots=filled_parameters,
                missing_slot_name=missing_param
            )
            self._states[user_id] = state

            # Generate a question for the user
            missing_param_schema = param_schema['properties'][missing_param]
            question = call_llm_for_clarification_question(missing_param, missing_param_schema)
            return question
        else:
            # All required parameters are filled, we can execute the command
            self.clear_state(user_id)
            # In a real system, you'd now dispatch the tool execution
            return f"Отлично, все данные собраны. Выполняю {tool_name} с параметрами: {json.dumps(filled_parameters, ensure_ascii=False)}"

    def handle_user_response(self, user_id: str, text: str) -> Optional[str]:
        """
        Handles a follow-up message from a user who is in a dialogue state.

        Returns:
            A message for the user, or None if the conversation did not progress.
        """
        state = self.get_state(user_id)
        if not state or not state.missing_slot_name:
            return None # Not in a slot-filling dialogue

        # The user's text is assumed to be the answer for the missing slot
        state.filled_slots[state.missing_slot_name] = text

        # We can now re-run the slot-filling logic with the new information
        return self.start_slot_filling(user_id, state.active_tool_name, state.filled_slots)
