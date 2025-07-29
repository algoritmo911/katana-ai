import asyncio
from rich.console import Console
from katana.orchestrator.step import Step, StepResult, StepExecutor

console = Console()

class RunStep(Step):
    async def execute(self) -> StepResult:
        command = self.action.get("run")
        if not command:
            return StepResult(False, "No command specified for run step.")

        console.print(f"Running command: {command}")
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            console.print(f"Finished running command: {command}")
            return StepResult(True, stdout.decode())
        else:
            console.print(f"Error running command: {command}")
            return StepResult(False, stderr.decode())

class RunStepExecutor(StepExecutor):
    def can_handle(self, step_type):
        return step_type == "run"

    def create_step(self, id, action, context):
        return RunStep(id, action, context)
