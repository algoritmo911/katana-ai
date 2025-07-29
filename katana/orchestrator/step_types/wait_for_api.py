import asyncio
import httpx
from rich.console import Console
from katana.orchestrator.step import Step, StepResult, StepExecutor

console = Console()

class WaitForApiStep(Step):
    async def execute(self) -> StepResult:
        url = self.action.get("wait_for_api", {}).get("url")
        if not url:
            return StepResult(False, "No URL specified for wait_for_api step.")

        status_code = self.action.get("wait_for_api", {}).get("status", 200)
        timeout = self.action.get("wait_for_api", {}).get("timeout", 60)

        console.print(f"Waiting for API at {url}...")
        start_time = asyncio.get_event_loop().time()
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    response = await client.get(url)
                    if response.status_code == status_code:
                        console.print(f"API at {url} is ready.")
                        return StepResult(True)
                except httpx.RequestError:
                    pass
                if asyncio.get_event_loop().time() - start_time > timeout:
                    return StepResult(False, f"Timeout waiting for API at {url}.")
                await asyncio.sleep(1)

class WaitForApiStepExecutor(StepExecutor):
    def can_handle(self, step_type):
        return step_type == "wait_for_api"

    def create_step(self, id, action, context):
        return WaitForApiStep(id, action, context)
