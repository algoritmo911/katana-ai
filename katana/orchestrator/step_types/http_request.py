import httpx
from rich.console import Console
from katana.orchestrator.step import Step, StepResult, StepExecutor

console = Console()

class HttpRequestStep(Step):
    async def execute(self) -> StepResult:
        url = self.action.get("http_request", {}).get("url")
        if not url:
            return StepResult(False, "No URL specified for http_request step.")

        method = self.action.get("http_request", {}).get("method", "GET")
        headers = self.action.get("http_request", {}).get("headers")
        json = self.action.get("http_request", {}).get("json")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, url, headers=headers, json=json)
                response.raise_for_status()
                return StepResult(True, response.text)
            except httpx.HTTPStatusError as e:
                return StepResult(False, f"HTTP error: {e}")
            except httpx.RequestError as e:
                return StepResult(False, f"Request error: {e}")

class HttpRequestStepExecutor(StepExecutor):
    def can_handle(self, step_type):
        return step_type == "http_request"

    def create_step(self, id, action, context):
        return HttpRequestStep(id, action, context)
