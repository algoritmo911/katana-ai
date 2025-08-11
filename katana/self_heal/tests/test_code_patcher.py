import pytest
from unittest.mock import MagicMock, mock_open
from katana.self_heal.code_patcher import CodePatcher

@pytest.fixture
def mock_openai_client(monkeypatch):
    mock_client_instance = MagicMock()
    mock_client_instance.generate_text.return_value = "x = 0\ny = x + 5"

    mock_client_class = MagicMock(return_value=mock_client_instance)
    monkeypatch.setattr("katana.self_heal.code_patcher.OpenAIClient", mock_client_class)
    return mock_client_instance

def test_generate_patch_success(monkeypatch, mock_openai_client):
    # Arrange
    patcher = CodePatcher()
    analysis = {
        "file": "src/dummy_file.py",
        "line": 5,
        "root_cause_hypothesis": "The variable `x` was not initialized."
    }
    dummy_code = "def my_function():\n    y = x + 5\n"

    monkeypatch.setattr("os.path.exists", lambda path: True)
    m = mock_open(read_data=dummy_code)
    monkeypatch.setattr("builtins.open", m)

    # Act
    result = patcher.generate_patch(analysis)

    # Assert
    assert "original_snippet" in result
    assert "patched_snippet" in result
    assert result["patched_snippet"] == "x = 0\ny = x + 5"
    mock_openai_client.generate_text.assert_called_once()

def test_generate_patch_invalid_analysis(mock_openai_client):
    # Arrange
    patcher = CodePatcher()
    invalid_analysis = {"file": "src/dummy_file.py"}

    # Act
    result = patcher.generate_patch(invalid_analysis)

    # Assert
    assert "error" in result
    assert result["error"] == "Invalid analysis format provided."

def test_generate_patch_file_not_found(monkeypatch, mock_openai_client):
    # Arrange
    patcher = CodePatcher()
    analysis = {
        "file": "src/dummy_file.py",
        "line": 5,
        "root_cause_hypothesis": "The variable `x` was not initialized."
    }
    monkeypatch.setattr("os.path.exists", lambda path: False)

    # Act
    result = patcher.generate_patch(analysis)

    # Assert
    assert "error" in result
    assert result["error"] == f"File not found: {analysis['file']}"
