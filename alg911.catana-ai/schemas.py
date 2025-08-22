from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


# =======================================================================================================================
# Schemas for the OODA-P Tactical Loop
# =======================================================================================================================

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

# =======================================================================================================================
# Schemas for the Telos Meta-Cognitive Loop
# =======================================================================================================================

class NeurovaultSummary(BaseModel):
    """Summary of the Neurovault's state."""
    total_concepts: int
    total_relationships: int
    consistency: float

class DiagnostReport(BaseModel):
    """Summary of the Diagnost's system health report."""
    cpu_load_percent: float
    memory_usage_mb: float
    system_fatigue_index: float
    dependencies: Dict[str, str]

class CassandraPrediction(BaseModel):
    """Summary of Cassandra's predictions."""
    probability_critical_failure: float
    expected_user_queries: int
    system_fatigue_trend: float
    predictability_score: float

class WorldStateSnapshot(BaseModel):
    """
    Represents a coherent, probabilistic model of the agent's reality at a point in time.
    This is the output of the WorldModeler and the input for the DreamEngine.
    """
    timestamp: str = Field(..., description="The ISO 8601 timestamp of when the snapshot was created.")
    knowledge: NeurovaultSummary
    system_health: DiagnostReport
    predictions: CassandraPrediction
    action_history: List[Dict[str, Any]] = Field(..., description="A list of recent actions taken by the agent.")

class PossibleFutureNode(BaseModel):
    """
    Represents a single node in the "Nebula of Possible Futures" graph.
    Each node is a potential state of the world resulting from a sequence of actions.
    """
    node_id: str = Field(..., description="A unique identifier for this future node.")
    parent_id: Optional[str] = Field(None, description="The ID of the parent node in the simulation tree.")
    state: WorldStateSnapshot = Field(..., description="The world state at this node.")
    action_taken: Optional[Dict[str, Any]] = Field(None, description="The action taken from the parent state to reach this state.")
    depth: int = Field(..., description="The depth of this node in the simulation tree.")
    value_score: Optional[float] = Field(None, description="The desirability score assigned by the Value Judgement Engine (Phase 3).")
    children_ids: List[str] = Field(default_factory=list, description="A list of IDs of child nodes.")


if __name__ == '__main__':
    # Example Usage for Tactical Loop Schemas
    print("--- Tactical Loop Schemas ---")
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
