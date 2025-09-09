import pytest
import json
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from daemons.orchestrator.dsl import AgentDefinition
from daemons.orchestrator.runtime import AgentRuntime
from daemons.orchestrator.interpreter import StrategyInterpreter

# A minimal, valid AgentDefinition for testing
@pytest.fixture
def sample_agent_def_dict():
    return {
        "apiVersion": "prometheus.katana.ai/v1alpha1",
        "kind": "AutonomousTradingAgent",
        "metadata": {"name": "test-runtime-agent"},
        "spec": {
            "state": {
                "isHolding": {"type": "bool", "initialValue": False}
            },
            "sources": [],
            "triggers": [
                {"on": "test.trigger", "name": "test_trigger", "evaluates": "main_logic"}
            ],
            "strategy": {
                "main_logic": {
                    "steps": [
                        {"condition": {"type": "state.is_false", "inputs": {"input": "state.isHolding"}}},
                        {"actions": [{"type": "state.set", "parameters": {"variable": "isHolding", "value": True}}]}
                    ]
                }
            }
        }
    }

@pytest.fixture
def sample_agent_def(sample_agent_def_dict):
    return AgentDefinition(**sample_agent_def_dict)

@pytest.fixture
def mock_nats_client():
    return AsyncMock()

# --- Interpreter Tests ---

@pytest.mark.asyncio
async def test_interpreter_condition_state_is_false(mock_nats_client):
    interpreter = StrategyInterpreter("test-agent", mock_nats_client)
    state = {"isHolding": False}
    inputs = {"input": "state.isHolding"}
    result = await interpreter._handle_condition_state_is_false(inputs, state)
    assert result is True

    state["isHolding"] = True
    result = await interpreter._handle_condition_state_is_false(inputs, state)
    assert result is False

@pytest.mark.asyncio
async def test_interpreter_action_state_set(mock_nats_client):
    interpreter = StrategyInterpreter("test-agent", mock_nats_client)
    state = {"isHolding": False}
    parameters = {"variable": "isHolding", "value": True}
    await interpreter._handle_action_state_set(parameters, state)
    assert state["isHolding"] is True

@pytest.mark.asyncio
async def test_interpreter_action_hephaestus_trade(mock_nats_client):
    interpreter = StrategyInterpreter("test-agent", mock_nats_client)
    parameters = {"action": "BUY", "amount": 1}
    await interpreter._handle_action_hephaestus_trade(parameters, {})

    mock_nats_client.publish.assert_awaited_once()
    subject = mock_nats_client.publish.call_args[0][0]
    payload = json.loads(mock_nats_client.publish.call_args[0][1].decode())

    assert subject == "agent.test-agent.action.execute"
    assert payload["type"] == "hephaestus.trade"
    assert payload["parameters"]["action"] == "BUY"

# --- Runtime Tests ---

@pytest.mark.asyncio
async def test_runtime_initialization(sample_agent_def, mock_nats_client):
    runtime = AgentRuntime(sample_agent_def, mock_nats_client)
    assert runtime.agent_id == "test-runtime-agent"
    assert runtime.state == {"isHolding": False}
    assert isinstance(runtime.interpreter, StrategyInterpreter)

@pytest.mark.asyncio
async def test_runtime_start_subscribes_to_triggers(sample_agent_def, mock_nats_client):
    runtime = AgentRuntime(sample_agent_def, mock_nats_client)
    await runtime.start()
    await asyncio.sleep(0.01) # Allow the event loop to run the task

    # Check that subscribe was called with the trigger subject
    mock_nats_client.subscribe.assert_awaited_once()
    assert mock_nats_client.subscribe.call_args[0][0] == "test.trigger"
    assert callable(mock_nats_client.subscribe.call_args[1]['cb'])

    await runtime.stop() # Clean up the task

@pytest.mark.asyncio
async def test_runtime_trigger_executes_strategy(sample_agent_def, mock_nats_client):
    # --- Setup ---
    # Capture the callback function that the runtime creates
    captured_cb = None
    async def capture_cb_subscribe(subject, cb):
        nonlocal captured_cb
        captured_cb = cb
        return AsyncMock() # Return a mock subscription object

    mock_nats_client.subscribe.side_effect = capture_cb_subscribe

    runtime = AgentRuntime(sample_agent_def, mock_nats_client)
    await runtime.start()
    await asyncio.sleep(0.01) # Allow the event loop to run the task

    # Ensure the callback was captured
    assert captured_cb is not None

    # --- Run ---
    # Manually call the captured callback with a mock message
    mock_msg = MagicMock(subject="test.trigger")
    await captured_cb(mock_msg)

    # --- Assertions ---
    # The strategy should have run and changed the state
    assert runtime.state["isHolding"] is True

    await runtime.stop()
