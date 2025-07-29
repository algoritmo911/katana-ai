import json
from click.testing import CliRunner
from katana.cli import main

def test_history_default():
    """
    Test the history command with default options.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["history"])
    assert result.exit_code == 0
    assert "Katana AI Command History" in result.output

def test_history_json_output():
    """
    Test the history command with JSON output.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["history", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)

def test_history_user_filter():
    """
    Test the history command with the --user filter.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["history", "--user", "jules"])
    assert result.exit_code == 0
    assert "jules" in result.output
    assert "guest" not in result.output
