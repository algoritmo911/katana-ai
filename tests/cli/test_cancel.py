from click.testing import CliRunner
from katana.cli import main

def test_cancel_success():
    """
    Test the cancel command with a valid task ID.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["cancel", "123"])
    assert result.exit_code == 0
    assert "Task 123 cancelled" in result.output

def test_cancel_not_found():
    """
    Test the cancel command with an invalid task ID.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["cancel", "456"])
    assert result.exit_code == 0
    assert "Task not found" in result.output
