import unittest
from unittest.mock import patch, MagicMock
import sys

from katana.self_heal import cli

class TestCli(unittest.TestCase):

    @patch("argparse.ArgumentParser")
    def test_main_self_heal(self, MockArgumentParser):
        # Arrange
        mock_args = MagicMock()
        mock_args.command = "self-heal"
        mock_args.trace_id = "trace-123"

        mock_parser = MockArgumentParser.return_value
        mock_parser.parse_args.return_value = mock_args

        with patch("katana.self_heal.cli.SelfHealOrchestrator") as MockOrchestrator:
            mock_orchestrator_instance = MockOrchestrator.return_value

            # Act
            cli.main()

            # Assert
            MockOrchestrator.assert_called_once()
            mock_orchestrator_instance.run.assert_called_with("trace-123")

    @patch("argparse.ArgumentParser")
    def test_main_diagnose_log(self, MockArgumentParser):
        # Arrange
        mock_args = MagicMock()
        mock_args.command = "diagnose"
        mock_args.log_file = "test.log"
        mock_args.module_path = None
        mock_args.expected_hash = None

        mock_parser = MockArgumentParser.return_value
        mock_parser.parse_args.return_value = mock_args

        with patch("katana.self_heal.cli.diagnostics") as mock_diagnostics:
            mock_diagnostics.analyze_logs.return_value = ([], "No errors")

            # Act
            cli.main()

            # Assert
            mock_diagnostics.analyze_logs.assert_called_with("test.log")

    @patch("argparse.ArgumentParser")
    def test_main_diagnose_integrity(self, MockArgumentParser):
        # Arrange
        mock_args = MagicMock()
        mock_args.command = "diagnose"
        mock_args.log_file = None
        mock_args.module_path = "/path/to/module"
        mock_args.expected_hash = "hash"

        mock_parser = MockArgumentParser.return_value
        mock_parser.parse_args.return_value = mock_args

        with patch("katana.self_heal.cli.diagnostics") as mock_diagnostics:
            mock_diagnostics.check_module_integrity.return_value = (True, "OK")

            # Act
            cli.main()

            # Assert
            mock_diagnostics.check_module_integrity.assert_called_with("/path/to/module", "hash")

    @patch("argparse.ArgumentParser")
    def test_main_patch_restart(self, MockArgumentParser):
        # Arrange
        mock_args = MagicMock()
        mock_args.command = "patch"
        mock_args.restart_service = "test_service"
        mock_args.apply_patch = None
        mock_args.rollback = None
        mock_args.fetch_patch = None

        mock_parser = MockArgumentParser.return_value
        mock_parser.parse_args.return_value = mock_args

        with patch("katana.self_heal.cli.patch_applicator") as mock_patch_applicator:
            mock_patch_applicator.restart_service.return_value = (True, "OK")

            # Act
            cli.main()

            # Assert
            mock_patch_applicator.restart_service.assert_called_with("test_service")

    @patch("argparse.ArgumentParser")
    def test_main_patch_apply(self, MockArgumentParser):
        # Arrange
        mock_args = MagicMock()
        mock_args.command = "patch"
        mock_args.restart_service = None
        mock_args.apply_patch = "test.patch"
        mock_args.rollback = None
        mock_args.fetch_patch = None

        mock_parser = MockArgumentParser.return_value
        mock_parser.parse_args.return_value = mock_args

        with patch("katana.self_heal.cli.patch_applicator") as mock_patch_applicator:
            mock_patch_applicator.apply_patch.return_value = (True, "OK")

            # Act
            cli.main()

            # Assert
            mock_patch_applicator.apply_patch.assert_called_with("test.patch")

    @patch("argparse.ArgumentParser")
    def test_main_patch_rollback(self, MockArgumentParser):
        # Arrange
        mock_args = MagicMock()
        mock_args.command = "patch"
        mock_args.restart_service = None
        mock_args.apply_patch = None
        mock_args.rollback = True
        mock_args.fetch_patch = None

        mock_parser = MockArgumentParser.return_value
        mock_parser.parse_args.return_value = mock_args

        with patch("katana.self_heal.cli.patch_applicator") as mock_patch_applicator:
            mock_patch_applicator.rollback_changes.return_value = (True, "OK")

            # Act
            cli.main()

            # Assert
            mock_patch_applicator.rollback_changes.assert_called_once()

    @patch("argparse.ArgumentParser")
    def test_main_patch_fetch(self, MockArgumentParser):
        # Arrange
        mock_args = MagicMock()
        mock_args.command = "patch"
        mock_args.restart_service = None
        mock_args.apply_patch = None
        mock_args.rollback = None
        mock_args.fetch_patch = "http://example.com/patch"

        mock_parser = MockArgumentParser.return_value
        mock_parser.parse_args.return_value = mock_args

        with patch("katana.self_heal.cli.patch_applicator") as mock_patch_applicator:
            mock_patch_applicator.fetch_patch.return_value = ("patch content", "OK")

            # Act
            cli.main()

            # Assert
            mock_patch_applicator.fetch_patch.assert_called_with("http://example.com/patch")

if __name__ == "__main__":
    unittest.main()
