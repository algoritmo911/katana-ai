import pytest
from katana.orchestrator.runner import Orchestrator
from katana.orchestrator.context import Context
import os

@pytest.mark.asyncio
async def test_orchestrator_with_on_fail():
    """
    Test the orchestrator with an on_fail section.
    """
    scenario = {
        "steps": [
            {
                "id": "step1",
                "run": "exit 1",
                "on_fail": [
                    {
                        "id": "on_fail_step",
                        "run": "echo 'on_fail'"
                    }
                ]
            }
        ]
    }
    context = Context()
    orchestrator = Orchestrator(scenario, context)
    await orchestrator.run()
    assert context.get_result("on_fail_step") is not None

@pytest.mark.asyncio
async def test_orchestrator_with_rollback():
    """
    Test the orchestrator with a rollback section.
    """
    scenario = {
        "steps": [
            {
                "id": "step1",
                "run": "exit 1"
            }
        ],
        "rollback": [
            {
                "id": "rollback_step",
                "run": "echo 'rollback'"
            }
        ]
    }
    context = Context()
    orchestrator = Orchestrator(scenario, context)
    await orchestrator.run()
    assert context.get_result("rollback_step") is not None
