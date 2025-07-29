import asyncio
import time
from rich.console import Console

console = Console()

from katana.orchestrator.step_types.run import RunStepExecutor
from katana.orchestrator.step_types.wait import WaitStepExecutor
from katana.orchestrator.step_types.wait_for_file import WaitForFileStepExecutor
from katana.orchestrator.step_types.parallel import ParallelStepExecutor
from katana.orchestrator.step_types.rollback import RollbackStepExecutor
from katana.orchestrator.step_types.http_request import HttpRequestStepExecutor
from katana.orchestrator.step_types.wait_for_api import WaitForApiStepExecutor
from katana.orchestrator.utils.logger import setup_logger, JsonTrace
import time

class Orchestrator:
    def __init__(self, scenario, context):
        self.scenario = scenario
        self.context = context
        self.logger = setup_logger("orchestrator", "orchestrator.log")
        self.tracer = JsonTrace("run_trace.json")
        self.step_executors = [
            RunStepExecutor(),
            WaitStepExecutor(),
            WaitForFileStepExecutor(),
            RollbackStepExecutor(),
            HttpRequestStepExecutor(),
            WaitForApiStepExecutor(),
        ]
        self.step_executors.append(ParallelStepExecutor(self.step_executors))

    async def run(self):
        steps = self.scenario.get("steps", [])
        try:
            for i, step_action in enumerate(steps):
                step_id = step_action.get("id", f"step_{i}")
                step_type = [key for key in step_action.keys() if key not in ["id", "on_fail", "retry"]][0]

                executor = self.get_executor(step_type)
                if not executor:
                    self.logger.error(f"Unknown step type: {step_type}")
                    continue

                step = executor.create_step(step_id, step_action, self.context)

                retries = step_action.get("retry", 0)
                for i in range(retries + 1):
                    start_time = time.time()
                    result = await step.execute()
                    end_time = time.time()
                    if result.success:
                        self.logger.info(f"Step {step_id} succeeded.")
                        self.tracer.add_step_trace(step_id, "success", start_time, end_time, result.message)
                        self.context.set_result(step_id, result.message)
                        break
                    else:
                        self.logger.error(f"Step {step_id} failed: {result.message}")
                        if i < retries:
                            self.logger.info(f"Retrying step {step_id}...")
                            await asyncio.sleep(1)
                        else:
                            self.tracer.add_step_trace(step_id, "failed", start_time, end_time, result.message)
                            on_fail = step_action.get("on_fail")
                            if on_fail:
                                await self.run_on_fail(on_fail)
                            raise Exception("Scenario failed")
        except Exception:
            self.logger.error("Scenario failed.")
            rollback_steps = self.scenario.get("rollback")
            if rollback_steps:
                await self.run_rollback(rollback_steps)
        finally:
            self.tracer.save()

    def get_executor(self, step_type):
        for executor in self.step_executors:
            if executor.can_handle(step_type):
                return executor
        return None

    async def run_on_fail(self, on_fail_steps):
        console.print("Running on_fail steps...")
        for step_action in on_fail_steps:
            step_id = step_action.get("id", "on_fail_step")
            step_type = [key for key in step_action.keys() if key not in ["id", "on_fail", "retry"]][0]
            executor = self.get_executor(step_type)
            if executor:
                step = executor.create_step(step_id, step_action, self.context)
                result = await step.execute()
                if result.success:
                    self.context.set_result(step_id, result.message)

    async def run_rollback(self, rollback_steps):
        console.print("Running rollback steps...")
        for step_action in rollback_steps:
            step_id = step_action.get("id", "rollback_step")
            step_type = [key for key in step_action.keys() if key not in ["id", "on_fail", "retry"]][0]
            executor = self.get_executor(step_type)
            if executor:
                step = executor.create_step(step_id, step_action, self.context)
                result = await step.execute()
                if result.success:
                    self.context.set_result(step_id, result.message)

async def run_scenario(scenario, context):
    """
    Runs a scenario.
    """
    orchestrator = Orchestrator(scenario, context)
    await orchestrator.run()
