import asyncio
import random
from typing import List, Dict, Any
from src.orchestrator.task_orchestrator import TaskResult # Importing TaskResult

class BaseAgent:
    def __init__(self, processing_time_min: float = 0.5, processing_time_max: float = 2.0):
        """
        Initializes BaseAgent.
        This is a base class for any agent that can process tasks.
        processing_time_min: Minimum simulated time to process a task.
        processing_time_max: Maximum simulated time to process a task.
        """
        self.processing_time_min = processing_time_min
        self.processing_time_max = processing_time_max

    async def handle_single_task(self, task: Dict[str, Any]) -> TaskResult: # Task is now a Dict
        """
        Simulates processing a single task.
        This method would contain the actual logic for an agent to handle a task.
        """
        task_id = task.get("id", "N/A")
        print(f"BaseAgent starting task: {task_id}")
        # Simulate work being done
        await asyncio.sleep(random.uniform(self.processing_time_min, self.processing_time_max))

        # Simulate success/failure
        # For now, let's assume a 80% success rate for simulation
        is_success = random.random() < 0.8
        details = ""
        if is_success:
            details = f"Task '{task_id}' completed successfully by BaseAgent."
            print(f"BaseAgent completed task: {task_id}")
        else:
            details = f"Task '{task_id}' failed during processing by BaseAgent."
            print(f"BaseAgent failed task: {task_id}")

        return TaskResult(success=is_success, details=details, task_content=task)

    async def process_tasks(self, tasks: List[Dict[str, Any]]) -> List[TaskResult]:
        """
        Processes a list of tasks in parallel.
        """
        if not tasks:
            return []

        print(f"BaseAgent received batch of {len(tasks)} tasks.")
        # Process tasks in parallel
        results = await asyncio.gather(*(self.handle_single_task(task) for task in tasks))
        return results

# Example of how it might be used (optional, for direct testing of the agent)
async def main_agent_test():
    agent = BaseAgent()
    sample_tasks = [
        {"id": "task_1", "description": "Analyze user sentiment from last 20 comments."},
        {"id": "task_2", "description": "Generate a report on Q3 sales figures."},
        {"id": "task_3", "description": "Draft an email to congratulate top performers."}
    ]
    results = await agent.process_tasks(sample_tasks)
    for result in results:
        print(f"Task: {result.task_content['id']}, Success: {result.success}, Details: {result.details}")

if __name__ == "__main__":
    # This is just for testing BaseAgent independently.
    # The orchestrator will call process_tasks.
    # asyncio.run(main_agent_test())
    pass
