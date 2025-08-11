import unittest
from unittest.mock import patch, MagicMock

from katana.self_heal.orchestrator import SelfHealOrchestrator

class TestSelfHealOrchestrator(unittest.TestCase):

    @patch("katana.self_heal.orchestrator.FailureAnalyzer")
    @patch("katana.self_heal.orchestrator.CodePatcher")
    @patch("katana.self_heal.orchestrator.PatchValidator")
    @patch("katana.self_heal.orchestrator.create_pull_request")
    def test_run_success(self, mock_create_pr, MockPatchValidator, MockCodePatcher, MockFailureAnalyzer):
        # Arrange
        # Mock FailureAnalyzer
        mock_analyzer_instance = MockFailureAnalyzer.return_value
        mock_analyzer_instance.analyze.return_value = {
            "file": "test.py",
            "line": 10,
            "root_cause_hypothesis": "It broke."
        }

        # Mock CodePatcher
        mock_patcher_instance = MockCodePatcher.return_value
        mock_patcher_instance.generate_patch.return_value = {
            "original_snippet": "broken_code",
            "patched_snippet": "fixed_code"
        }

        # Mock PatchValidator
        mock_validator_instance = MockPatchValidator.return_value
        mock_validator_instance.validate_patch.return_value = True

        orchestrator = SelfHealOrchestrator()

        # Act
        orchestrator.run("trace-123")

        # Assert
        mock_analyzer_instance.analyze.assert_called_with("trace-123")
        mock_patcher_instance.generate_patch.assert_called_once()
        mock_validator_instance.validate_patch.assert_called_with("test.py", "broken_code", "fixed_code")
        # As per instructions, we are not calling create_pull_request
        mock_create_pr.assert_not_called()

    @patch("katana.self_heal.orchestrator.FailureAnalyzer")
    @patch("katana.self_heal.orchestrator.CodePatcher")
    @patch("katana.self_heal.orchestrator.PatchValidator")
    def test_run_analysis_fails(self, MockPatchValidator, MockCodePatcher, MockFailureAnalyzer):
        # Arrange
        mock_analyzer_instance = MockFailureAnalyzer.return_value
        mock_analyzer_instance.analyze.return_value = {"error": "Analysis failed"}

        mock_patcher_instance = MockCodePatcher.return_value

        orchestrator = SelfHealOrchestrator()

        # Act
        orchestrator.run("trace-123")

        # Assert
        mock_analyzer_instance.analyze.assert_called_with("trace-123")
        # Other components should not be called
        mock_patcher_instance.generate_patch.assert_not_called()

if __name__ == "__main__":
    unittest.main()
