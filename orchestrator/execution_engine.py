import asyncio
from typing import Dict, Any

from orchestrator.planner import ExecutionPlan, ExecutionStep
from orchestrator.registry import get_capability

class ExecutionState:
    """A simple class to hold the state of a plan's execution."""
    def __init__(self, plan: ExecutionPlan):
        self.plan = plan
        # Stores the output of each step, keyed by step_id
        self.step_outputs: Dict[int, Any] = {}
        # Stores any errors that occur, keyed by step_id
        self.step_errors: Dict[int, str] = {}

    def add_output(self, step_id: int, output: Any):
        """Adds the successful output of a step to the state."""
        self.step_outputs[step_id] = output

    def add_error(self, step_id: int, error_message: str):
        """Adds the error message of a failed step to the state."""
        self.step_errors[step_id] = error_message

    def __str__(self):
        return f"ExecutionState(outputs={self.step_outputs}, errors={self.step_errors})"

async def execute_plan(plan: ExecutionPlan) -> ExecutionState:
    """
    Asynchronously executes a given ExecutionPlan.

    This engine iterates through each step of the plan, finds the corresponding
    capability in the registry, validates inputs, executes the function, and
    stores the result.
    """
    print(f"\n--- Starting Execution of Plan for Goal: '{plan.goal}' ---")
    state = ExecutionState(plan)

    for step in sorted(plan.steps, key=lambda s: s.step_id):
        print(f"\n[Executing Step {step.step_id}: {step.capability_name}]")
        print(f"  Reasoning: {step.reasoning}")
        print(f"  Parameters: {step.parameters}")

        try:
            # 1. Find the capability in the registry
            capability = get_capability(step.capability_name)

            # 2. Validate parameters against the input schema
            # Pydantic v2 uses `model_validate` instead of `parse_obj`
            input_data = capability.input_schema.model_validate(step.parameters)

            # 3. Execute the capability's function
            # We check if the function is a coroutine and await it if so.
            if asyncio.iscoroutinefunction(capability.function):
                output = await capability.function(input_data)
            else:
                output = capability.function(input_data)

            # 4. Store the output
            state.add_output(step.step_id, output)
            print(f"  ✅ Step {step.step_id} successful.")
            print(f"  Output: {output.model_dump_json(indent=2) if hasattr(output, 'model_dump_json') else output}")

        except Exception as e:
            error_message = f"Error during execution of step {step.step_id}: {e}"
            print(f"  ❌ Step {step.step_id} failed: {error_message}")
            state.add_error(step.step_id, error_message)
            # For now, we stop execution on the first error.
            # The Self-Correction Loop will later handle this more gracefully.
            break

    print("\n--- Plan Execution Finished ---")
    return state
