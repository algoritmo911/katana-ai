import pytest
from katana.orchestrator.runner import run_scenario
from katana.orchestrator.context import Context

@pytest.mark.asyncio
async def test_run_scenario():
    """
    Test running a scenario.
    """
    steps = [
        {"run": "echo 'hello'"},
        {"wait": 1},
    ]
    context = Context()
    await run_scenario(steps, context)
