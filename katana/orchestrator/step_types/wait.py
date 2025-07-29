import asyncio
from rich.console import Console
from katana.orchestrator.step import Step, StepResult, StepExecutor

console = Console()

class WaitStep(Step):
    async def execute(self) -> StepResult:
        duration = self.action.get("wait")
        if not isinstance(duration, int):
            return StepResult(False, "No duration specified for wait step.")

        console.print(f"Waiting for {duration} seconds...")
        await asyncio.sleep(duration)
        console.print("Finished waiting.")
        return StepResult(True)

class WaitStepExecutor(StepExecutor):
    def can_handle(self, step_type):
        return step_type == "wait"

    def create_step(self, id, action, context):
        return WaitStep(id, action, context)
