import asyncio
from rich.console import Console
from katana.orchestrator.step import Step, StepResult, StepExecutor

console = Console()

class ParallelStep(Step):
    def __init__(self, id, action, context, step_executors):
        super().__init__(id, action, context)
        self.step_executors = step_executors

    async def execute(self) -> StepResult:
        steps_to_run = self.action.get("parallel")
        if not isinstance(steps_to_run, list):
            return StepResult(False, "No steps specified for parallel step.")

        tasks = []
        for i, step_action in enumerate(steps_to_run):
            step_id = f"{self.id}_{i}"
            step_type = list(step_action.keys())[0]
            for executor in self.step_executors:
                if executor.can_handle(step_type):
                    step = executor.create_step(step_id, step_action, self.context)
                    tasks.append(step.execute())
                    break

        results = await asyncio.gather(*tasks)
        for result in results:
            if not result.success:
                return StepResult(False, f"A step in the parallel block failed: {result.message}")

        return StepResult(True)


class ParallelStepExecutor(StepExecutor):
    def __init__(self, step_executors):
        self.step_executors = step_executors

    def can_handle(self, step_type):
        return step_type == "parallel"

    def create_step(self, id, action, context):
        return ParallelStep(id, action, context, self.step_executors)
