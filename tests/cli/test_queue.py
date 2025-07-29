import json
from click.testing import CliRunner
from katana.cli import main

def test_queue_default():
    """
    Test the queue command with default options.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["queue"])
    assert result.exit_code == 0
    assert "Katana AI Command Queue" in result.output

def test_queue_json_output():
    """
    Test the queue command with JSON output.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["queue", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
