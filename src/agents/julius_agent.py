import asyncio
import random
from typing import List
from src.orchestrator.task_orchestrator import TaskResult # Importing TaskResult

class JuliusAgent:
    def __init__(self, processing_time_min: float = 0.5, processing_time_max: float = 2.0):
        """
        Initializes JuliusAgent.
        processing_time_min: Minimum simulated time to process a task.
        processing_time_max: Maximum simulated time to process a task.
        """
        self.processing_time_min = processing_time_min
        self.processing_time_max = processing_time_max

    async def handle_single_task(self, task: str) -> TaskResult:
        """
        Simulates processing a single task.
        This method would contain the actual logic for Julius to handle a task.
        """
        print(f"Julius starting task: {task}")
        # Simulate work being done
        await asyncio.sleep(random.uniform(self.processing_time_min, self.processing_time_max))

        # Simulate success/failure
        # For now, let's assume a 80% success rate for simulation
        is_success = random.random() < 0.8
        details = ""
        if is_success:
            details = f"Task '{task}' completed successfully by Julius."
            print(f"Julius completed task: {task}")
        else:
            details = f"Task '{task}' failed during processing by Julius."
            print(f"Julius failed task: {task}")

        return TaskResult(success=is_success, details=details, task_content=task)

    async def process_tasks(self, tasks: List[str]) -> List[TaskResult]:
        """
        Processes a list of tasks, either sequentially or in parallel.
        For this implementation, we'll run them in parallel using asyncio.gather.
        """
        if not tasks:
            return []

        print(f"Julius received batch of {len(tasks)} tasks.")
        # Process tasks in parallel
        results = await asyncio.gather(*(self.handle_single_task(task) for task in tasks))
        return results

# Example of how it might be used (optional, for direct testing of the agent)
async def main_agent_test():
    agent = JuliusAgent()
    sample_tasks = [
        "Analyze user sentiment from last 20 comments.",
        "Generate a report on Q3 sales figures.",
        "Draft an email to congratulate top performers."
    ]
    results = await agent.process_tasks(sample_tasks)
    for result in results:
        print(f"Task: {result.task_content}, Success: {result.success}, Details: {result.details}")

if __name__ == "__main__":
    # This is just for testing JuliusAgent independently.
    # The orchestrator will call process_tasks.
    # asyncio.run(main_agent_test())
    pass
