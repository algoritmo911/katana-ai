from click.testing import CliRunner
from katana.cli import main

def test_ping():
    """
    Test the ping command.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["ping"])
    assert result.exit_code == 0
    assert "Pong!" in result.output
