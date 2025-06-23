import asyncio
from typing import List
from src.orchestrator.task_orchestrator import TaskResult # Importing TaskResult

# Attempt to import KatanaAgent, but fall back to a mock if not available
try:
    from src.agents.katana_agent import KatanaAgent # Assuming KatanaAgent is in this location
except ImportError:
    print("Warning: KatanaAgent not found. Using a mock implementation for JuliusAgent.")
    # Define a mock KatanaAgent if the real one isn't available
    # This mock should have the same interface as the real KatanaAgent
    class KatanaAgent:
        async def process_tasks(self, tasks: List[str]) -> List[TaskResult]:
            print(f"Mock KatanaAgent processing tasks: {tasks}")
            # Simulate some processing delay
            await asyncio.sleep(1)
            # Simulate all tasks succeeding for simplicity in the mock
            return [TaskResult(success=True, details=f"Mock KatanaAgent processed task: {task}", task_content=task) for task in tasks]

class JuliusAgent: # This class will now act as a wrapper or utilize KatanaAgent
    def __init__(self, use_katana: bool = True, **kwargs):
        """
        Initializes JuliusAgent.
        If use_katana is True, it will try to use KatanaAgent.
        Otherwise, it can fall back to a different behavior or raise an error.
        **kwargs are passed to KatanaAgent if it's used.
        """
        self.use_katana = use_katana
        if self.use_katana:
            try:
                self.katana_agent = KatanaAgent(**kwargs)
                print("JuliusAgent initialized with KatanaAgent.")
            except NameError: # KatanaAgent was not imported
                 print("ERROR: KatanaAgent is not defined. JuliusAgent cannot use KatanaAgent.")
                 # Fallback: use a mock agent or raise an exception.
                 # For now, let's make it use a mock version if KatanaAgent is not available at runtime
                 # This is a bit redundant with the import-level mock, but provides an instance-level fallback
                 self.katana_agent = self._create_mock_katana_agent()
                 print("JuliusAgent falling back to internal mock KatanaAgent due to initialization error.")
            except Exception as e:
                print(f"Error initializing KatanaAgent: {e}. JuliusAgent will use a mock.")
                self.katana_agent = self._create_mock_katana_agent()
        else:
            # If not using Katana, define what JuliusAgent should do.
            # For now, let's assume it must use Katana or a mock of it.
            print("JuliusAgent initialized without KatanaAgent (use_katana=False). Using a mock KatanaAgent.")
            self.katana_agent = self._create_mock_katana_agent()


    def _create_mock_katana_agent(self):
        """Creates a mock KatanaAgent instance for fallback."""
        class MockKatanaAgent:
            async def process_tasks(self, tasks: List[str]) -> List[TaskResult]:
                print(f"Internal Mock KatanaAgent processing tasks: {tasks}")
                await asyncio.sleep(0.5) # Shorter delay for internal mock
                return [TaskResult(success=True, details=f"Internal Mock KatanaAgent processed task: {task}", task_content=task) for task in tasks]
        return MockKatanaAgent()

    async def process_tasks(self, tasks: List[str]) -> List[TaskResult]:
        """
        Processes a list of tasks using KatanaAgent.
        """
        if not tasks:
            return []

        print(f"JuliusAgent (using Katana) received batch of {len(tasks)} tasks.")
        # Delegate to KatanaAgent's process_tasks method
        results = await self.katana_agent.process_tasks(tasks)
        return results

# Example of how it might be used (optional, for direct testing of the agent)
async def main_agent_test():
    # Test with KatanaAgent (or its mock if not found)
    agent_with_katana = JuliusAgent(use_katana=True)
    sample_tasks = [
        "Analyze user sentiment from last 20 comments via Katana.",
        "Generate a report on Q3 sales figures via Katana.",
    ]
    print("\n--- Testing JuliusAgent with KatanaAgent (or mock) ---")
    results_katana = await agent_with_katana.process_tasks(sample_tasks)
    for result in results_katana:
        print(f"Task: {result.task_content}, Success: {result.success}, Details: {result.details}")

    # Example: Test without explicitly using Katana (falls back to mock)
    agent_without_katana_explicit = JuliusAgent(use_katana=False)
    sample_tasks_non_katana = [
        "Draft an email to congratulate top performers (non-Katana path)."
    ]
    print("\n--- Testing JuliusAgent with use_katana=False (uses mock) ---")
    results_non_katana = await agent_without_katana_explicit.process_tasks(sample_tasks_non_katana)
    for result in results_non_katana:
        print(f"Task: {result.task_content}, Success: {result.success}, Details: {result.details}")


if __name__ == "__main__":
    # This is just for testing JuliusAgent independently.
    # The orchestrator will call process_tasks.
    # To run this test: python -m src.agents.julius_agent
    asyncio.run(main_agent_test())
    pass
