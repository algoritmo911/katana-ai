import os
import pytest
from unittest.mock import patch
from datetime import date

from src.oracle.scanner import GitHubScanner
from src.oracle.models import SpecialistProfile
from src.hephaestus.generator import TestGenerator


@patch('src.oracle.scanner.GitHubScanner._fetch_github_data')
def test_symbiosis_end_to_end_pipeline(mock_fetch_github_data):
    """
    A full end-to-end test simulating the "Oracle" -> "Hephaestus" pipeline.
    """
    # 1. Arrange: Define a virtual specialist, their code, and the tools.
    specialist_username = "e2e_specialist"
    # A simple function to be "analyzed" and tested.
    specialist_source_code = "def is_palindrome(s: str) -> bool:\n    return s == s[::-1]"

    scanner = GitHubScanner()
    generator = TestGenerator()

    # Arrange mock for the Oracle part of the pipeline.
    # The scanner will "find" this data for our specialist.
    mock_fetch_github_data.return_value = {
        "github_username": specialist_username,
        "languages": ["Python"],
        "skill_level": 9,
        "last_commit_date": date.today(),
    }

    # 2. Act: Execute the main cycle of the prototype.
    # - "Oracle" analyzes the profile.
    profile = scanner.analyze(specialist_username)

    # - "Hephaestus" takes the code and generates a test.
    generated_test_script = generator.generate(specialist_source_code)

    # 3. Assert: Verify the results of the pipeline.
    # - Check if the Oracle part worked as expected.
    mock_fetch_github_data.assert_called_once_with(specialist_username)
    assert isinstance(profile, SpecialistProfile)
    assert profile.github_username == specialist_username

    # - Check if the Hephaestus part produced valid-looking code.
    assert generated_test_script is not None
    assert "import pytest" in generated_test_script
    assert "def test_is_palindrome_placeholder():" in generated_test_script
    assert "assert True" in generated_test_script # Check for the placeholder test

    # - Finally, prove the generated product is viable by running it.
    temp_test_filename = "tests/temp_e2e_generated_test.py"
    try:
        with open(temp_test_filename, "w") as f:
            f.write(generated_test_script)

        # Run pytest on the generated file and check for a success exit code.
        exit_code = pytest.main([temp_test_filename, "-q"])
        assert exit_code == 0, "The E2E generated test script failed to execute or pass."

    finally:
        # Ensure cleanup of the temporary file.
        if os.path.exists(temp_test_filename):
            os.remove(temp_test_filename)
