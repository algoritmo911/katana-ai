# This script is the final verification for the entire Orchestrator architecture.
# It tests the full think-act-correct loop.

import asyncio
# Import all tools to ensure they are registered in the Capability Registry
import tools.code_profiler
import tools.static_analyzer
from orchestrator.main import run_orchestrator

async def main():
    print("==========================================================")
    print("= Running Verification for the Complete Orchestrator     =")
    print("==========================================================")

    # --- Test Case 1: Success on First Try ---
    print("\n\n--- TEST CASE 1: SUCCESS ON FIRST TRY ---")
    success_goal = "Profile the module at `src/core/app.py`"
    success_state = await run_orchestrator(success_goal)
    print(f"\nFinal state for success case: {success_state}")
    assert not success_state.step_errors, "Success case should have no errors!"
    assert 1 in success_state.step_outputs, "Success case should have an output for step 1!"
    print("\n--- TEST CASE 1 PASSED ---")


    # --- Test Case 2: Failure and Self-Correction ---
    print("\n\n--- TEST CASE 2: FAILURE AND SELF-CORRECTION ---")
    failure_goal = "Profile the module at `src/fail/module.py`"
    failure_state = await run_orchestrator(failure_goal)
    print(f"\nFinal state for failure case: {failure_state}")
    assert not failure_state.step_errors, "Failure case should ultimately succeed with no errors!"
    assert 1 in failure_state.step_outputs, "Failure case should have an output for the corrected step 1!"
    # Check that the output is from the *second* tool, the static analyzer
    output_json = failure_state.step_outputs[1].model_dump()
    assert "findings" in output_json, "Corrected plan should have run the static analyzer!"
    print("\n--- TEST CASE 2 PASSED ---")


    print("\n\n==========================================================")
    print("= Orchestrator Verification Complete: All tests passed! =")
    print("==========================================================")


if __name__ == "__main__":
    asyncio.run(main())
