import pytest
import os
from unittest.mock import patch, MagicMock

from katana.self_heal.failure_analyzer import FailureAnalyzer

@pytest.fixture
def log_file():
    log_file_path = "test.log"
    with open(log_file_path, "w") as f:
        f.write("[2023-10-27 10:00:00] [INFO] [trace-123] Starting operation.\n")
        f.write("[2023-10-27 10:00:01] [ERROR] [trace-123] An error occurred!\n")
        f.write("[trace-123] Traceback (most recent call last):\n")
        f.write('[trace-123]   File "katana/core/state.py", line 112, in handle_request\n')
        f.write("[trace-123]     user_session.update(data)\n")
        f.write("[trace-123] AttributeError: 'NoneType' object has no attribute 'update'\n")
    yield log_file_path
    os.remove(log_file_path)

@patch("katana.self_heal.failure_analyzer.OpenAIClient")
def test_analyze_success(MockOpenAIClient, log_file):
    # Arrange
    mock_nlp_instance = MockOpenAIClient.return_value
    mock_nlp_instance.generate_text.return_value = "The user_session was None."

    os.environ["LOG_FILE_PATH"] = log_file
    analyzer = FailureAnalyzer()

    # Act
    result = analyzer.analyze("trace-123")

    # Assert
    assert result["file"] == "katana/core/state.py"
    assert result["line"] == 112
    assert result["root_cause_hypothesis"] == "The user_session was None."
    mock_nlp_instance.generate_text.assert_called_once()

@patch("katana.self_heal.failure_analyzer.OpenAIClient")
def test_analyze_no_trace_id(MockOpenAIClient, log_file):
    # Arrange
    os.environ["LOG_FILE_PATH"] = log_file
    analyzer = FailureAnalyzer()

    # Act
    result = analyzer.analyze("trace-456")

    # Assert
    assert "error" in result
    assert result["error"] == "No logs found for trace_id: trace-456"

def test_extract_file_and_line():
    # Arrange
    traceback_str = '  File "katana/core/state.py", line 112, in handle_request\n'

    # Act
    file_path, line_num = FailureAnalyzer._extract_file_and_line(traceback_str)

    # Assert
    assert file_path == "katana/core/state.py"
    assert line_num == 112
