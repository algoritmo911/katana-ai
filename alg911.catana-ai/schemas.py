from pydantic import BaseModel, Field
from typing import List, Dict, Any
from enum import Enum

class CommandType(str, Enum):
    """
    Enumeration for the type of command to be executed.
    """
    LOCAL_PYTHON = "local_python"
    N8N_WEBHOOK = "n8n_webhook"

class Command(BaseModel):
    """
    Represents a single, concrete action to be performed by the TaskExecutor.
    """
    name: str = Field(..., description="The name of the command to execute, e.g., 'send_telegram_message' or 'n8n_workflow_abc'.")
    type: CommandType = Field(..., description="The type of the command, determining how it will be executed.")
    params: Dict[str, Any] = Field(default_factory=dict, description="A dictionary of parameters for the command.")

class Plan(BaseModel):
    """
    Represents a sequence of commands to achieve a specific high-level goal.
    """
    goal: str = Field(..., description="The high-level goal that this plan is designed to achieve.")
    plan_id: str = Field(..., description="A unique identifier for this plan instance.")
    steps: List[Command] = Field(..., description="The sequence of commands to execute to fulfill the plan.")

# Example Usage (for clarity, not part of the core schema definitions)
if __name__ == '__main__':
    # Example of a plan to answer a user's question
    example_plan = Plan(
        goal="answer_user_question",
        plan_id="plan-12345-abcdef",
        steps=[
            Command(
                name="memory.retrieve_full_context",
                type=CommandType.LOCAL_PYTHON,
                params={"user_id": "user456"}
            ),
            Command(
                name="nlp.generate_answer",
                type=CommandType.LOCAL_PYTHON,
                params={"context_data": "{step_0_output}"} # Placeholder for data from previous step
            ),
            Command(
                name="send_message_via_n8n",
                type=CommandType.N8N_WEBHOOK,
                params={
                    "webhook_url": "https://n8n.example.com/webhook/send-telegram",
                    "user_id": "user456",
                    "text": "{step_1_output}" # Placeholder for data from previous step
                }
            )
        ]
    )

    print("Example Plan:")
    print(example_plan.model_dump_json(indent=2))
