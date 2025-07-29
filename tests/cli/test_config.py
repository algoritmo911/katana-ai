from click.testing import CliRunner
from katana.cli import main

def test_config_show_empty(monkeypatch, tmp_path):
    """
    Test the config show command with no config file.
    """
    config_file = tmp_path / ".katana" / "config.json"
    monkeypatch.setattr("katana.core.cli_logic.config.CONFIG_FILE", config_file)
    runner = CliRunner()
    result = runner.invoke(main, ["config", "show"])
    assert result.exit_code == 0
    assert "No configuration set" in result.output

def test_config_set_and_show(monkeypatch, tmp_path):
    """
    Test the config set and show commands.
    """
    config_file = tmp_path / ".katana" / "config.json"
    monkeypatch.setattr("katana.core.cli_logic.config.CONFIG_FILE", config_file)
    runner = CliRunner()
    result = runner.invoke(main, ["config", "set", "endpoint", "http://localhost:3000"])
    assert result.exit_code == 0
    assert "Config value 'endpoint' set to 'http://localhost:3000'" in result.output

    result = runner.invoke(main, ["config", "show"])
    assert result.exit_code == 0
    assert "endpoint" in result.output
    assert "http://localhost:3000" in result.output
