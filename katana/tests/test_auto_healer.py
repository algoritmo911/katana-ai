import pytest
from unittest.mock import MagicMock, patch
import yaml

from katana.auto_healer import AutoHealer, ReflexMap

@pytest.fixture
def mock_reflex_map_content():
    """Provides a mock reflex map for testing."""
    return {
        "anomalies": [
            {
                "name": "test_anomaly_1",
                "workflow": "run_test_workflow_1",
                "params": {"param_a": "value_a"},
            },
            {
                "name": "test_anomaly_2_no_params",
                "workflow": "run_test_workflow_2",
            },
        ]
    }

@pytest.fixture
def mock_reflex_map_file(tmp_path, mock_reflex_map_content):
    """Creates a temporary reflex map YAML file."""
    file_path = tmp_path / "reflex_map.yml"
    with open(file_path, 'w') as f:
        yaml.dump(mock_reflex_map_content, f)
    return str(file_path)

def test_reflex_map_loading(mock_reflex_map_file, mock_reflex_map_content):
    """Tests that the ReflexMap class loads the YAML file correctly."""
    reflex_map = ReflexMap(file_path=mock_reflex_map_file)
    # Access internal for testing purposes
    assert reflex_map._reflex_map == mock_reflex_map_content

def test_get_workflow_for_anomaly(mock_reflex_map_file):
    """Tests retrieving a workflow from the reflex map."""
    reflex_map = ReflexMap(file_path=mock_reflex_map_file)

    # Test for an anomaly that exists
    workflow_info = reflex_map.get_workflow_for_anomaly("test_anomaly_1")
    assert workflow_info is not None
    assert workflow_info["workflow"] == "run_test_workflow_1"
    assert workflow_info["params"] == {"param_a": "value_a"}

    # Test for an anomaly with no params
    workflow_info_2 = reflex_map.get_workflow_for_anomaly("test_anomaly_2_no_params")
    assert workflow_info_2 is not None
    assert workflow_info_2["workflow"] == "run_test_workflow_2"
    assert workflow_info_2["params"] == {} # Should default to empty dict

    # Test for an anomaly that does not exist
    workflow_info_none = reflex_map.get_workflow_for_anomaly("non_existent_anomaly")
    assert workflow_info_none is None

@patch('katana.auto_healer.logger')
def test_auto_healer_handles_known_anomaly(mock_logger, mock_reflex_map_file):
    """Tests that the AutoHealer correctly handles a known anomaly."""
    reflex_map = ReflexMap(file_path=mock_reflex_map_file)
    auto_healer = AutoHealer(reflex_map)

    anomaly_data = {"name": "test_anomaly_1", "details": {"host": "server-1"}}
    auto_healer.handle_anomaly(anomaly_data)

    # Check that the action was logged via the critical logger
    mock_logger.critical.assert_called_once()
    call_args = mock_logger.critical.call_args[0][0]

    assert call_args["event"] == "auto_healer_action"
    assert call_args["anomaly_name"] == "test_anomaly_1"
    assert call_args["corrective_action"]["workflow_name"] == "run_test_workflow_1"
    assert call_args["corrective_action"]["parameters"] == {"param_a": "value_a"}

@patch('katana.auto_healer.logger')
def test_auto_healer_handles_unknown_anomaly(mock_logger, mock_reflex_map_file):
    """Tests that the AutoHealer logs a warning for an unknown anomaly."""
    reflex_map = ReflexMap(file_path=mock_reflex_map_file)
    auto_healer = AutoHealer(reflex_map)

    anomaly_data = {"name": "unknown_anomaly", "details": {}}
    auto_healer.handle_anomaly(anomaly_data)

    # Check that a warning was logged and no critical action was taken
    mock_logger.warning.assert_called_with("No workflow found for anomaly: unknown_anomaly. No action taken.")
    mock_logger.critical.assert_not_called()

@patch('katana.auto_healer.logger')
def test_auto_healer_handles_anomaly_with_no_name(mock_logger, mock_reflex_map_file):
    """Tests that the AutoHealer ignores an anomaly with no name."""
    reflex_map = ReflexMap(file_path=mock_reflex_map_file)
    auto_healer = AutoHealer(reflex_map)

    anomaly_data = {"details": {"info": "some data"}} # No 'name' key
    auto_healer.handle_anomaly(anomaly_data)

    # Check that a warning was logged and no other action was taken
    mock_logger.warning.assert_called_with("Received anomaly with no name. Ignoring.")
    mock_logger.critical.assert_not_called()
