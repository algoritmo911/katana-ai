import asyncio
from typing import List, Dict

# --- Mock Dependencies ---

class MockGitClient:
    """A mock client to simulate Git operations."""
    async def create_branch(self, branch_name: str) -> bool:
        print(f"GIT: Creating new isolated branch: '{branch_name}'")
        await asyncio.sleep(0.1)
        return True

    async def merge_branch(self, branch_name: str) -> bool:
        print(f"GIT: Merging successful branch '{branch_name}' into main.")
        await asyncio.sleep(0.2)
        return True

    async def delete_branch(self, branch_name: str) -> bool:
        print(f"GIT: Deleting failed branch '{branch_name}' to roll back changes.")
        await asyncio.sleep(0.1)
        return True

class MockCenturion:
    """A mock client to simulate running a full test suite."""
    async def run_quality_gate(self, branch_name: str) -> bool:
        print(f"CENTURION: Running full test suite on branch '{branch_name}'...")
        await asyncio.sleep(3) # Testing takes time
        # We can simulate failure for specific goals
        if "fail_test" in branch_name:
            print("CENTURION: ❌ Tests FAILED.")
            return False
        print("CENTURION: ✅ All tests PASSED.")
        return True

class MockOrchestrator:
    """A mock orchestrator to simulate executing a goal."""
    async def run(self, goal: str) -> bool:
        print(f"ORCHESTRATOR: Executing goal: '{goal}'")
        await asyncio.sleep(2)
        # Simulate the orchestrator's own self-correction failing
        if "fail_orchestrator" in goal:
            print("ORCHESTRATOR: ❌ Goal execution FAILED.")
            return False
        print("ORCHESTRATOR: ✅ Goal execution SUCCEEDED.")
        return True

# --- Main Executor Class ---

class REMExecutor:
    """
    Executes a prioritized list of tasks using a safe, isolated workflow.
    """
    def __init__(self, orchestrator, git_client, centurion_gate):
        self.orchestrator = orchestrator
        self.git = git_client
        self.centurion = centurion_gate

    async def execute_task_list(self, tasks: List[Dict]):
        print(f"REM_EXECUTOR: Starting execution of {len(tasks)} prioritized tasks.")
        for i, task in enumerate(tasks):
            print(f"\n--- Starting task {i+1}/{len(tasks)}: {task['goal']} ---")

            branch_name = f"morpheus/task-{i+1}-{task['raw_finding']['type']}"

            # 1. Isolate Environment
            await self.git.create_branch(branch_name)

            # 2. Invoke Orchestrator
            success = await self.orchestrator.run(task['goal'])

            if not success:
                print("REM_EXECUTOR: Orchestrator failed to achieve its goal. Abandoning task.")
                await self.git.delete_branch(branch_name)
                continue # Move to the next task

            # 3. Post-Execution Verification
            tests_passed = await self.centurion.run_quality_gate(branch_name)

            # 4. Evaluate and Finalize
            if tests_passed:
                print("REM_EXECUTOR: ✅ Task successfully executed and verified. Merging changes.")
                await self.git.merge_branch(branch_name)
                # TODO: Add Memory Consolidation step here
            else:
                print("REM_EXECUTOR: ❌ Task failed verification. Rolling back changes.")
                await self.git.delete_branch(branch_name)

        print("\nREM_EXECUTOR: All tasks processed.")

async def run_executor_simulation():
    """A helper function to simulate the executor for testing."""
    from .architect import DreamArchitect
    from .analyzer import DreamAnalyzer, MockCodeScanner, MockOracleClient, MockNoosphereClient

    print("\n--- Running REM Executor Simulation (Full Loop) ---")

    # 1. Get a report
    analyzer = DreamAnalyzer(MockCodeScanner(), MockOracleClient(), MockNoosphereClient())
    report = await analyzer.run_diagnostics()

    # 2. Get a plan
    architect = DreamArchitect()
    tasks = architect.generate_tasks(report)
    # Add a failing task for demonstration
    tasks.append({
        "goal": "Refactor a critical component that will fail_test.",
        "raw_finding": {"type": "code_debt"}
    })
    prioritized_tasks = architect.prioritize_tasks(tasks)

    # 3. Execute the plan
    executor = REMExecutor(MockOrchestrator(), MockGitClient(), MockCenturion())
    await executor.execute_task_list(prioritized_tasks)

    print("\n--- Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(run_executor_simulation())
