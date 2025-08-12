import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from orchestrator.registry import get_all_capabilities_for_llm

# --- Plan Data Structures ---

class ExecutionStep(BaseModel):
    """Represents a single step in an execution plan."""
    step_id: int = Field(..., description="A unique identifier for the step within the plan.")
    capability_name: str = Field(..., description="The name of the capability to be executed, must match a name in the Capability Registry.")
    parameters: Dict[str, Any] = Field(..., description="A dictionary of parameters to pass to the capability's input schema.")
    reasoning: str = Field(..., description="The LLM's reasoning for why this step is necessary.")

class ExecutionPlan(BaseModel):
    """Represents a full, multi-step plan to achieve a user's goal."""
    goal: str = Field(..., description="The original user goal this plan aims to solve.")
    steps: List[ExecutionStep] = Field(..., description="The sequence of steps to be executed.")

# --- Prompt Engineering ---

def create_planner_prompt(user_goal: str) -> str:
    """
    Creates the system prompt for the LLM planner, including the goal and available tools.
    """
    capabilities_list_str = get_all_capabilities_for_llm()

    prompt = f"""
You are an expert AI orchestrator. Your task is to create a detailed, step-by-step execution plan
to achieve a user's goal. You have access to a set of tools (capabilities), and you must use them
to build the plan.

**User's Goal:**
{user_goal}

**Available Capabilities:**
{capabilities_list_str}

**Instructions:**
1.  Analyze the user's goal.
2.  Review the available capabilities.
3.  Create a JSON object representing the execution plan.
4.  The plan must be a list of steps. Each step must include the `capability_name`, the `parameters` for that capability, and your `reasoning` for including this step.
5.  The output MUST be a valid JSON object of type `ExecutionPlan`. Do not add any extra text or explanations outside of the JSON structure.
6.  If the goal cannot be achieved with the available tools, you must respond with an empty list of steps and a reasoning that explains why.

**Output Format Example:**
{{
    "goal": "User's goal here",
    "steps": [
        {{
            "step_id": 1,
            "capability_name": "some_capability_name",
            "parameters": {{
                "param1": "value1",
                "param2": "value2"
            }},
            "reasoning": "This step is needed to do X, which is a prerequisite for Y."
        }},
        {{
            "step_id": 2,
            "capability_name": "another_capability",
            "parameters": {{
                "input_data": "output_from_step_1"
            }},
            "reasoning": "This step processes the output of the previous step to achieve Z."
        }}
    ]
}}

Now, generate the plan for the user's goal.
"""
    return prompt

# --- Prompt Engineering for Re-planning ---

def create_replanner_prompt(user_goal: str, failed_plan: ExecutionPlan, error_message: str) -> str:
    """
    Creates a system prompt for the LLM to generate a *new* plan after a failure.
    """
    capabilities_list_str = get_all_capabilities_for_llm()

    prompt = f"""
You are an expert AI orchestrator. Your previous attempt to solve the user's goal failed.
You must now create a new plan to achieve the goal, taking the failure into account.

**User's Goal:**
{user_goal}

**Previous Plan That Failed:**
{failed_plan.model_dump_json(indent=2)}

**Error Encountered:**
{error_message}

**Available Capabilities:**
{capabilities_list_str}

**Instructions:**
1.  Analyze the original goal and why the previous plan failed.
2.  Devise a new, alternative strategy. Do not simply repeat the failed step.
3.  If there is a different tool that can accomplish a similar goal, consider using it.
4.  Create a new JSON object representing the new execution plan.
5.  The output MUST be a valid JSON object of type `ExecutionPlan`.

Now, generate a new plan.
"""
    return prompt


# --- Mock Planner ---

def generate_plan_mock(user_goal: str, failed_plan: ExecutionPlan = None, error_message: str = None) -> ExecutionPlan:
    """
    A mock function that simulates a call to an LLM planner.

    If `failed_plan` is provided, it simulates re-planning. Otherwise, it generates an initial plan.
    """
    if failed_plan:
        # --- This is the Self-Correction / Re-planning path ---
        print("--- Generating Re-Planner Prompt (Self-Correction) ---")
        prompt = create_replanner_prompt(user_goal, failed_plan, error_message)
        print(prompt)
        print("--- (Mocking LLM Re-planning Response) ---")

        # In the mock, if the profiler failed, we switch to the static analyzer.
        mock_llm_output = {
            "goal": user_goal,
            "steps": [
                {
                    "step_id": 1,
                    "capability_name": "run_static_analyzer",
                    "parameters": {
                        "module_path": failed_plan.steps[0].parameters.get("module_path")
                    },
                    "reasoning": "The initial plan to use the full profiler failed because the module was too large. As an alternative, I will use the lightweight `run_static_analyzer` to get the cyclomatic complexity and other potential issues without the performance overhead."
                }
            ]
        }
    else:
        # --- This is the Initial Planning path ---
        print("--- Generating Initial Planner Prompt ---")
        prompt = create_planner_prompt(user_goal)
        print(prompt)
        print("--- (Mocking LLM Initial Response) ---")

        # The initial plan always tries the profiler first.
        # The module path is extracted from the goal for the mock.
        module_path = user_goal.split("`")[1] if "`" in user_goal else "src/core/main.py"
        mock_llm_output = {
            "goal": user_goal,
            "steps": [
                {
                    "step_id": 1,
                    "capability_name": "run_code_profiler",
                    "parameters": {
                        "module_path": module_path,
                        "line_limit": 15
                    },
                    "reasoning": "The user wants to analyze the performance of a module. The `run_code_profiler` capability is the perfect tool for this. I will start by running it on the specified module."
                }
            ]
        }

    plan = ExecutionPlan.model_validate(mock_llm_output)
    return plan
