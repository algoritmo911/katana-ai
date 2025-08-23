from pydantic import BaseModel, Field, root_validator
from typing import Dict, List, Any, Optional, Literal

# Low-level components of the strategy definition
class Condition(BaseModel):
    """Defines a condition to be evaluated."""
    type: str
    inputs: Dict[str, Any]

class Action(BaseModel):
    """Defines an action to be executed."""
    type: str
    parameters: Dict[str, Any]

class Step(BaseModel):
    """
    A single step in a strategy, which can be either a condition to check
    or a list of actions to execute.
    """
    condition: Optional[Condition] = None
    actions: Optional[List[Action]] = None

    @root_validator(skip_on_failure=True)
    def check_exclusive_fields(cls, values):
        """Ensures that a step is either a condition or an action, but not both."""
        if sum(v is not None for v in values.values()) != 1:
            raise ValueError("A Step must contain exactly one of 'condition' or 'actions'.")
        return values

# Mid-level components that define an agent's behavior and state
class System(BaseModel):
    """A logical block within a strategy, composed of multiple steps."""
    description: Optional[str] = None
    steps: List[Step]

class StateVariable(BaseModel):
    """A variable defining a piece of the agent's internal state."""
    type: str
    initialValue: Any
    constraints: Optional[str] = None

class Source(BaseModel):
    """A data source that the agent subscribes to."""
    name: str
    type: str
    parameters: Dict[str, Any]

class Trigger(BaseModel):
    """An event that triggers the evaluation of a strategy system."""
    on: str
    name: str
    description: Optional[str] = None
    evaluates: str

# Top-level components that form the agent definition
class AgentSpec(BaseModel):
    """The specification of the agent's behavior, state, and triggers."""
    description: Optional[str] = None
    state: Dict[str, StateVariable]
    sources: List[Source]
    triggers: List[Trigger]
    strategy: Dict[str, System]

class AgentMetadata(BaseModel):
    """Metadata for the agent, such as its name and labels."""
    name: str
    labels: Optional[Dict[str, str]] = None

class AgentDefinition(BaseModel):
    """
    The root object for defining an autonomous agent according to the Prometheus DSL.
    """
    apiVersion: Literal["prometheus.katana.ai/v1alpha1"]
    kind: Literal["AutonomousTradingAgent"]
    metadata: AgentMetadata
    spec: AgentSpec
