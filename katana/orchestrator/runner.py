import asyncio
import time
from rich.console import Console

console = Console()

async def run_step(step, context):
    """
    Runs a single step in the scenario.
    """
    if "run" in step:
        command = step["run"]
        console.print(f"Running command: {command}")
        # In a real implementation, this would actually run the command.
        # For now, we will just simulate it.
        await asyncio.sleep(1)
        console.print(f"Finished running command: {command}")
    elif "wait" in step:
        duration = step["wait"]
        console.print(f"Waiting for {duration} seconds...")
        await asyncio.sleep(duration)
        console.print("Finished waiting.")

async def run_scenario(steps, context):
    """
    Runs a scenario.
    """
    for step in steps:
        await run_step(step, context)
