import asyncio
from typing import Optional

from orchestrator.planner import generate_plan_mock, ExecutionPlan
from orchestrator.execution_engine import execute_plan, ExecutionState

async def run_orchestrator(user_goal: str, max_retries: int = 2) -> ExecutionState:
    """
    The main orchestrator loop that embodies the think-act-correct cycle.

    1.  **Think**: Generates a plan to achieve the user's goal.
    2.  **Act**: Executes the plan.
    3.  **Correct**: If execution fails, it generates a new plan and retries.
    """
    print(f"--- Orchestrator Started for Goal: '{user_goal}' ---")

    current_plan: Optional[ExecutionPlan] = None
    last_error: Optional[str] = None
    execution_state: Optional[ExecutionState] = None

    for i in range(max_retries):
        print(f"\n--- Cycle {i + 1}/{max_retries} ---")

        # 1. Think (or Re-think)
        current_plan = generate_plan_mock(
            user_goal=user_goal,
            failed_plan=current_plan, # Pass the previous failed plan if it exists
            error_message=last_error
        )

        # 2. Act
        execution_state = await execute_plan(current_plan)

        # 3. Correct (Check for failure)
        if not execution_state.step_errors:
            print("\n✅ Orchestrator finished: Plan executed successfully.")
            return execution_state

        # Plan failed, prepare for next loop iteration
        last_error = list(execution_state.step_errors.values())[0]
        print(f"\n⚠️ Orchestrator cycle failed. Error: {last_error}")
        print("    Preparing to re-plan...")

    print(f"\n❌ Orchestrator finished: Goal could not be achieved after {max_retries} attempts.")
    return execution_state
