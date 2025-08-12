from typing import Callable, Dict, Type
from pydantic import BaseModel, Field

# --- Capability Registry ---
CAPABILITY_REGISTRY: Dict[str, "CapabilityContract"] = {}

class CapabilityContract(BaseModel):
    """
    Defines the contract for a capability that can be registered and used by the Orchestrator.
    This contract ensures that the planner has all necessary information to reason about the tool.
    """
    capability_name: str = Field(..., description="Unique identifier for the capability, e.g., 'run_code_analysis'.")
    description: str = Field(..., description="Natural language description of what the capability does. Used by the LLM planner.")
    input_schema: Type[BaseModel] = Field(..., description="Pydantic model defining the input parameters for the capability.")
    output_schema: Type[BaseModel] = Field(..., description="Pydantic model defining the output structure of the capability.")
    function: Callable = Field(..., description="The actual function to execute.", exclude=True) # Exclude from serialization

    class Config:
        arbitrary_types_allowed = True

def register_capability(
    capability_name: str,
    description: str,
    input_schema: Type[BaseModel],
    output_schema: Type[BaseModel]
) -> Callable:
    """
    A decorator to register a function as a Capability in the central registry.

    Args:
        capability_name: The unique name of the capability.
        description: A clear, natural language description for the LLM.
        input_schema: The Pydantic model for the function's inputs.
        output_schema: The Pydantic model for the function's outputs.

    Returns:
        A decorator that registers the function and returns it unmodified.
    """
    def decorator(func: Callable) -> Callable:
        contract = CapabilityContract(
            capability_name=capability_name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            function=func
        )
        if capability_name in CAPABILITY_REGISTRY:
            # This could be a warning or an error depending on desired behavior
            print(f"Warning: Overwriting already registered capability '{capability_name}'.")
        CAPABILITY_REGISTRY[capability_name] = contract
        return func
    return decorator

def get_capability(capability_name: str) -> CapabilityContract:
    """Retrieves a capability from the registry by its name."""
    if capability_name not in CAPABILITY_REGISTRY:
        raise ValueError(f"Capability '{capability_name}' not found in registry.")
    return CAPABILITY_REGISTRY[capability_name]

def get_all_capabilities_for_llm() -> str:
    """
    Serializes all registered capabilities into a string format
    suitable for inclusion in an LLM prompt.
    """
    if not CAPABILITY_REGISTRY:
        return "No capabilities registered."

    output_lines = ["Here is a list of available tools/capabilities:"]
    for name, contract in CAPABILITY_REGISTRY.items():
        output_lines.append(f"---")
        output_lines.append(f"Capability: `{name}`")
        output_lines.append(f"  Description: {contract.description}")
        output_lines.append(f"  Input Schema: {contract.input_schema.schema_json(indent=2)}")
        output_lines.append(f"  Output Schema: {contract.output_schema.schema_json(indent=2)}")
        output_lines.append(f"---")

    return "\n".join(output_lines)
