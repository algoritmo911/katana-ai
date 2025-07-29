import json
from click.testing import CliRunner
from katana.cli import main

def test_log_default():
    """
    Test the log command with default options.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["log"])
    assert result.exit_code == 0
    assert "Katana AI Logs" in result.output

def test_log_json_output():
    """
    Test the log command with JSON output.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["log", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)

def test_log_error_filter():
    """
    Test the log command with the --error filter.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["log", "--error"])
    assert result.exit_code == 0
    assert "ERROR" in result.output
    assert "INFO" not in result.output

def test_log_today_filter():
    """
    Test the log command with the --today filter.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["log", "--today"])
    assert result.exit_code == 0
    # This test is not very robust, as it depends on the mock data having a log from today.
    # A better approach would be to mock the datetime module.
    assert "Katana AI Logs" in result.output
