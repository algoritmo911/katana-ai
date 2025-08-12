import os
from unittest.mock import patch, MagicMock
import time
import pytest
from katana.telemetry.trace_command import trace_command
from katana.memory.core import MemoryCore

@pytest.fixture(autouse=True)
def setup_teardown():
    # Reset the global client instance before each test to ensure isolation
    patcher = patch('katana.telemetry.trace_command.supabase_memory_client_instance', None)
    patcher.start()
    yield
    patcher.stop()

@patch.object(MemoryCore, 'add_dialogue')
@patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "a.b.c"})
def test_trace_command_success_with_supabase(mock_add_dialogue):
    @trace_command(use_supabase=True, tags=["test_success"], user_id_arg_name="user")
    def sample_command_success(user: str, data: str):
        time.sleep(0.01) # Simulate work
        return {"status": "ok", "processed_data": data.upper()}

    result = sample_command_success(user="user_alpha", data="input_data")

    assert result == {"status": "ok", "processed_data": "INPUT_DATA"}
    mock_add_dialogue.assert_called_once()
    call_args = mock_add_dialogue.call_args[1]

    assert call_args['user_id'] == "user_alpha"
    assert call_args['command_name'] == "sample_command_success"
    assert "'user': 'user_alpha'" in str(call_args['input_data'])
    assert "'data': 'input_data'" in str(call_args['input_data'])
    assert call_args['output_data'] == {"status": "ok", "processed_data": "INPUT_DATA"}
    assert call_args['duration'] == pytest.approx(0.01, abs=0.005)
    assert call_args['success'] is True
    assert call_args['tags'] == ["test_success"]

@patch.object(MemoryCore, 'add_dialogue')
@patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "a.b.c"})
def test_trace_command_failure_with_supabase(mock_add_dialogue):
    @trace_command(use_supabase=True, tags=["test_failure"])
    def sample_command_failure(user_id: str):
        time.sleep(0.01) # Simulate work
        raise ValueError("Simulated error")

    with pytest.raises(ValueError):
        sample_command_failure(user_id="user_beta")

    mock_add_dialogue.assert_called_once()
    call_args = mock_add_dialogue.call_args[1]

    assert call_args['user_id'] == "user_beta"
    assert call_args['command_name'] == "sample_command_failure"
    assert "'user_id': 'user_beta'" in str(call_args['input_data'])
    assert call_args['output_data'] == {"error": "Simulated error"}
    assert call_args['duration'] == pytest.approx(0.01, abs=0.005)
    assert call_args['success'] is False
    assert call_args['tags'] == ["test_failure"]
