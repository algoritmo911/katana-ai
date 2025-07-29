import asyncio
import os
from rich.console import Console
from katana.orchestrator.step import Step, StepResult, StepExecutor

console = Console()

class WaitForFileStep(Step):
    async def execute(self) -> StepResult:
        file_path = self.action.get("wait_for_file")
        if not file_path:
            return StepResult(False, "No file path specified for wait_for_file step.")

        timeout = self.action.get("timeout", 60)
        console.print(f"Waiting for file {file_path}...")
        start_time = asyncio.get_event_loop().time()
        while True:
            if os.path.exists(file_path):
                console.print(f"File {file_path} found.")
                return StepResult(True)
            if asyncio.get_event_loop().time() - start_time > timeout:
                return StepResult(False, f"Timeout waiting for file {file_path}.")
            await asyncio.sleep(1)

class WaitForFileStepExecutor(StepExecutor):
    def can_handle(self, step_type):
        return step_type == "wait_for_file"

    def create_step(self, id, action, context):
        return WaitForFileStep(id, action, context)
