import json
from click.testing import CliRunner
from katana.cli import main

def test_status_no_auth(monkeypatch):
    """
    Test the status command without authentication.
    """
    monkeypatch.setenv("HOME", "/tmp")
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0
    assert "Authentication required" in result.output

def test_status_with_auth_token(monkeypatch):
    """
    Test the status command with an auth token provided via the --auth-token flag.
    """
    monkeypatch.setenv("HOME", "/tmp")
    runner = CliRunner()
    result = runner.invoke(main, ["--auth-token", "mysecrettoken", "status"])
    assert result.exit_code == 0
    assert "Katana AI Status" in result.output

def test_status_with_auth_file(monkeypatch, tmp_path):
    """
    Test the status command with an auth token provided via a file.
    """
    (tmp_path / ".katana").mkdir()
    (tmp_path / ".katana" / "cli_auth.json").write_text('{"token": "mysecrettokenfromfile"}')
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0
    assert "Katana AI Status" in result.output

def test_status_json_output(monkeypatch):
    """
    Test the status command with JSON output.
    """
    monkeypatch.setenv("HOME", "/tmp")
    runner = CliRunner()
    result = runner.invoke(main, ["--auth-token", "mysecrettoken", "status", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "status" in data
    assert "active_tasks" in data
    assert "command_queue" in data
    assert "errors" in data
