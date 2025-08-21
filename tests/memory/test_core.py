import os
from unittest.mock import patch, MagicMock
import json
import pytest
from katana.memory.core import MemoryCore

@pytest.fixture
def memory_core():
    with patch('katana.memory.core.create_client') as mock_create_client:
        mock_supabase_client = MagicMock()
        mock_create_client.return_value = mock_supabase_client
        with patch('katana.memory.core.VectorizationService'):
            mc = MemoryCore()
            mc.client = mock_supabase_client
            yield mc

@patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
def test_init_success(memory_core):
    assert memory_core.client is not None

@patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_KEY": ""})
def test_init_failure_missing_credentials(caplog):
    with caplog.at_level("WARNING"):
        mc = MemoryCore()
        assert mc.client is None
        assert "SUPABASE_URL and/or SUPABASE_KEY environment variables are not set" in caplog.text

@patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
def test_add_dialogue_success(memory_core):
    mock_response = MagicMock()
    mock_response.data = [{"id": 1, "user_id": "test_user"}]
    mock_response.error = None
    memory_core.client.table.return_value.insert.return_value.execute.return_value = mock_response

    result = memory_core.add_dialogue(
        user_id="test_user", command_name="test_cmd", input_data={},
        output_data={}, duration=0.1, success=True
    )
    assert result == {"id": 1, "user_id": "test_user"}
    assert memory_core.client.table.call_args_list[0].args[0] == "command_logs"


@patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
def test_get_dialogue_success(memory_core):
    mock_response = MagicMock()
    mock_response.data = [{"id": 1, "command_name": "test_cmd"}]
    mock_response.error = None
    memory_core.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
    result = memory_core.get_dialogue(1)
    assert result == [{"id": 1, "command_name": "test_cmd"}]

@patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
def test_add_dialogue_vectorization_failure(memory_core, caplog):
    """Test that dialogue creation succeeds even if vectorization fails."""
    mock_vectorize = memory_core.vectorization_service.vectorize
    mock_vectorize.return_value = None # Simulate vectorization failure

    mock_dialogue_response = MagicMock()
    mock_dialogue_response.data = [{"id": 123}]
    mock_dialogue_response.error = None

    memory_core.client.table.return_value.insert.return_value.execute.return_value = mock_dialogue_response

    with caplog.at_level("WARNING"):
        result = memory_core.add_dialogue("user1", "cmd", {"in": "a"}, {"out": "b"}, 0.1, True)
        # The original dialogue data should still be returned
        assert result == {"id": 123}
        assert "Could not generate embedding for dialogue_id: 123" in caplog.text

    mock_vectorize.assert_called_once()
    # Check that insert was only called once (for the dialogue)
    memory_core.client.table.return_value.insert.assert_called_once()
