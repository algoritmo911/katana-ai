import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from katana.modules.sync_agent import periodic_sync
from unittest.mock import patch

@patch('katana.modules.sync_agent.sync_memory_with_n8n')
def test_periodic_sync(mock_sync_memory):
    agent_memory_state = {"test": "data"}
    periodic_sync(agent_memory_state)
    mock_sync_memory.assert_called_once_with(agent_memory_state)
