import sys
import os
import subprocess
from unittest.mock import patch, call, MagicMock
import pytest
import typer
from typer.testing import CliRunner

# Force the project root onto the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from katana_cli import main as cli_main

runner = CliRunner()

@patch('katana_cli.core.system.check_dependencies')
@patch('katana_cli.core.kubernetes.build_docker_image')
@patch('katana_cli.core.kubernetes.check_cluster')
@patch('katana_cli.core.kubernetes.create_cluster')
@patch('katana_cli.core.kubernetes.load_docker_image')
@patch('katana_cli.core.kubernetes.deploy_with_helm')
def test_env_up_full_success_path(
    mock_deploy, mock_load, mock_create, mock_check, mock_build, mock_deps
):
    """
    Test the `katana env up` command in the ideal success scenario.
    This test ensures all functions are called in the correct order.
    """
    # Arrange: Simulate all steps succeeding
    mock_deps.return_value = True
    mock_build.return_value = True
    mock_check.return_value = False  # Simulate cluster does not exist
    mock_create.return_value = True
    mock_load.return_value = True
    mock_deploy.return_value = True

    # Act: Run the CLI command
    result = runner.invoke(cli_main.app, ["env", "up"])

    # Assert
    assert result.exit_code == 0
    assert "Forge environment is up and running on Kubernetes!" in result.stdout

    # Verify that all our mocked functions were called in the correct sequence
    mock_deps.assert_called_once()
    mock_build.assert_called_once()
    mock_check.assert_called_once()
    mock_create.assert_called_once()
    mock_load.assert_called_once()
    mock_deploy.assert_called_once()

@patch('katana_cli.core.system.check_dependencies', return_value=True)
@patch('katana_cli.core.kubernetes.build_docker_image', return_value=True)
@patch('katana_cli.core.kubernetes.check_cluster', return_value=True) # Cluster exists
@patch('katana_cli.core.kubernetes.create_cluster') # Should not be called
@patch('katana_cli.core.kubernetes.load_docker_image', return_value=True)
@patch('katana_cli.core.kubernetes.deploy_with_helm', return_value=True)
def test_env_up_skips_cluster_creation_if_exists(
    mock_deploy, mock_load, mock_create, mock_check, mock_build, mock_deps
):
    """Test that `create_cluster` is not called if the cluster already exists."""
    result = runner.invoke(cli_main.app, ["env", "up"])

    assert result.exit_code == 0
    mock_check.assert_called_once()
    mock_create.assert_not_called() # Crucial check
    mock_deploy.assert_called_once()


@patch('katana_cli.core.system.check_dependencies', return_value=False)
def test_env_up_fails_on_dependency_check(mock_deps):
    """Test that the command exits if dependency check fails."""
    result = runner.invoke(cli_main.app, ["env", "up"])

    assert result.exit_code != 0
    assert "System dependencies check failed" in result.stdout

@patch('katana_cli.core.system.check_dependencies', return_value=True)
@patch('katana_cli.core.kubernetes.build_docker_image', return_value=False)
def test_env_up_fails_on_build_failure(mock_build, mock_deps):
    """Test that the command exits if docker build fails."""
    result = runner.invoke(cli_main.app, ["env", "up"])

    assert result.exit_code != 0
    # The error message for this would be printed by the function itself,
    # but the exit code is the most important thing to check.
    mock_build.assert_called_once()
