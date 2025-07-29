from click.testing import CliRunner
from katana.cli import main

def test_flush_with_force():
    """
    Test the flush command with the --force flag.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["flush", "--force"])
    assert result.exit_code == 0
    assert "System flushed" in result.output

def test_flush_with_confirmation_yes():
    """
    Test the flush command with confirmation (yes).
    """
    runner = CliRunner()
    result = runner.invoke(main, ["flush"], input="y\n")
    assert result.exit_code == 0
    assert "System flushed" in result.output

def test_flush_with_confirmation_no():
    """
    Test the flush command with confirmation (no).
    """
    runner = CliRunner()
    result = runner.invoke(main, ["flush"], input="n\n")
    assert result.exit_code == 0
    assert "Flush cancelled" in result.output
