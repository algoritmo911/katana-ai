import pytest
import json
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock

# Add src directory to sys.path to allow importing streamlit_app
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "orchestrator"))

# Now import the function from streamlit_app
# We need to be careful if streamlit_app directly calls st functions at module level
# For now, assuming load_log_data is safe to import.
# If not, we might need to mock 'streamlit' module itself.
try:
    from streamlit_app import load_log_data
except ImportError as e:
    # This might happen if streamlit is not installed or if there's an issue with sys.path
    # For testing load_log_data, we primarily need the function itself.
    # If 'st' calls are problematic, we'll mock them within tests.
    print(f"Could not import streamlit_app: {e}. Will attempt to proceed with tests, mocking 'st' if necessary.")
    load_log_data = None # Placeholder

# Sample log data
SAMPLE_LOG_ENTRY_1 = {"round": 1, "timestamp": 1678886400, "batch_size": 10, "avg_time_per_task_seconds": 0.5, "error_types_in_batch": []}
SAMPLE_LOG_ENTRY_2 = {"round": 2, "timestamp": 1678886500, "batch_size": 15, "avg_time_per_task_seconds": 0.7, "error_types_in_batch": [{"type": "APIError", "count": 1}]}
SAMPLE_LOG_ENTRY_3 = {"round": 3, "timestamp": 1678886300, "batch_size": 5, "avg_time_per_task_seconds": 0.3, "error_types_in_batch": []} # Older timestamp


@pytest.fixture(autouse=True)
def mock_streamlit():
    """Automatically mock streamlit functions for all tests in this module."""
    # Mock 'st' module and its functions like st.warning, st.error
    # This prevents Streamlit's UI-specific calls from breaking tests
    # when running in a non-Streamlit environment.
    mock_st = MagicMock()
    with patch.dict('sys.modules', {'streamlit': mock_st}):
        # Re-import or reload the module that uses streamlit if it's already loaded
        # This is tricky. A cleaner way is to ensure streamlit_app.py doesn't call st functions
        # at the module level or during import of load_log_data.
        # For now, we'll assume load_log_data itself doesn't directly call st.X() that causes issues on import.
        # The calls within load_log_data (st.warning, st.error) will use the mocked object.
        global load_log_data
        if 'streamlit_app' in sys.modules:
            import importlib
            import streamlit_app as app_module
            importlib.reload(app_module)
            load_log_data = app_module.load_log_data
        else:
            from streamlit_app import load_log_data as lld
            load_log_data = lld

        yield mock_st # The mocked st object can be used in tests if needed

# Test cases
def test_load_log_data_valid_file(mock_streamlit):
    """Tests loading data from a valid JSONL log file."""
    if not load_log_data: pytest.skip("load_log_data not imported")
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmpfile:
        json.dump(SAMPLE_LOG_ENTRY_1, tmpfile)
        tmpfile.write("\n")
        json.dump(SAMPLE_LOG_ENTRY_2, tmpfile)
        tmpfile.write("\n")
        json.dump(SAMPLE_LOG_ENTRY_3, tmpfile) # Intentionally older for sorting test
        tmpfile.write("\n")
        tmpfile_path = Path(tmpfile.name)

    loaded_data = load_log_data(tmpfile_path)
    tmpfile_path.unlink() # Clean up

    assert loaded_data is not None
    assert len(loaded_data) == 3
    # Check sorting (newest first by timestamp)
    assert loaded_data[0]["round"] == SAMPLE_LOG_ENTRY_2["round"]
    assert loaded_data[1]["round"] == SAMPLE_LOG_ENTRY_1["round"]
    assert loaded_data[2]["round"] == SAMPLE_LOG_ENTRY_3["round"]
    assert mock_streamlit.warning.call_count == 0
    assert mock_streamlit.error.call_count == 0

def test_load_log_data_file_not_found(mock_streamlit):
    """Tests behavior when the log file does not exist."""
    if not load_log_data: pytest.skip("load_log_data not imported")
    non_existent_path = Path("non_existent_log_file.json")
    loaded_data = load_log_data(non_existent_path)
    assert loaded_data is None
    mock_streamlit.warning.assert_called_once()
    # Check that the warning message contains the filename
    args, _ = mock_streamlit.warning.call_args
    assert str(non_existent_path.name) in args[0]


def test_load_log_data_empty_file(mock_streamlit):
    """Tests loading data from an empty log file."""
    if not load_log_data: pytest.skip("load_log_data not imported")
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmpfile:
        # File is empty
        tmpfile_path = Path(tmpfile.name)

    loaded_data = load_log_data(tmpfile_path)
    tmpfile_path.unlink()

    assert loaded_data == [] # Should return an empty list
    assert mock_streamlit.warning.call_count == 0
    assert mock_streamlit.error.call_count == 0


def test_load_log_data_invalid_json_line(mock_streamlit):
    """Tests loading data from a file with one invalid JSON line."""
    if not load_log_data: pytest.skip("load_log_data not imported")
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmpfile:
        json.dump(SAMPLE_LOG_ENTRY_1, tmpfile)
        tmpfile.write("\n")
        tmpfile.write("this is not valid json\n")
        json.dump(SAMPLE_LOG_ENTRY_2, tmpfile)
        tmpfile.write("\n")
        tmpfile_path = Path(tmpfile.name)

    loaded_data = load_log_data(tmpfile_path)
    tmpfile_path.unlink()

    assert loaded_data is None # Should return None due to the strict error handling
    mock_streamlit.error.assert_called_once()
    args, _ = mock_streamlit.error.call_args
    assert "Error decoding JSON" in args[0]
    assert "this is not valid json" in args[0]


def test_load_log_data_not_jsonl(mock_streamlit):
    """Tests a file that is valid JSON but not JSONL (e.g. a list of objects)."""
    if not load_log_data: pytest.skip("load_log_data not imported")
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmpfile:
        # This is a JSON list, not JSONL
        json.dump([SAMPLE_LOG_ENTRY_1, SAMPLE_LOG_ENTRY_2], tmpfile)
        tmpfile_path = Path(tmpfile.name)

    loaded_data = load_log_data(tmpfile_path)
    tmpfile_path.unlink()

    # The current implementation tries to parse line by line.
    # If the whole file is a single line of a JSON array, it might fail json.loads(line)
    # or succeed if it's just one entry.
    # If the first line is "[..." and it's a large array, json.loads(line) will fail.
    # This behavior is acceptable as it expects JSONL.
    assert loaded_data is None # Expecting failure as it's not line-delimited JSON objects
    mock_streamlit.error.assert_called_once()
    args, _ = mock_streamlit.error.call_args
    assert "Error decoding JSON" in args[0] or "Failed to read or process" in args[0]


def test_load_log_data_empty_lines_and_whitespace(mock_streamlit):
    """Tests robustness against empty lines or lines with only whitespace."""
    if not load_log_data: pytest.skip("load_log_data not imported")
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmpfile:
        tmpfile.write("\n") # Empty line
        json.dump(SAMPLE_LOG_ENTRY_1, tmpfile)
        tmpfile.write("\n")
        tmpfile.write("   \n") # Line with whitespace
        json.dump(SAMPLE_LOG_ENTRY_2, tmpfile)
        tmpfile.write("\n")
        tmpfile_path = Path(tmpfile.name)

    loaded_data = load_log_data(tmpfile_path)
    tmpfile_path.unlink()

    assert loaded_data is not None
    assert len(loaded_data) == 2
    assert loaded_data[0]["round"] == SAMPLE_LOG_ENTRY_2["round"] # Check sorting
    assert loaded_data[1]["round"] == SAMPLE_LOG_ENTRY_1["round"]
    assert mock_streamlit.warning.call_count == 0
    assert mock_streamlit.error.call_count == 0

if __name__ == "__main__":
    # This allows running pytest directly on this file
    # e.g., python tests/orchestrator/test_streamlit_ui.py
    # Ensure pytest is installed and in PATH
    # Also ensure that the 'src/orchestrator' is in PYTHONPATH or sys.path manipulation works
    pytest.main([__file__])
