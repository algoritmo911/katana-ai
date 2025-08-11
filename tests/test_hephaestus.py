import os
import pytest
from src.hephaestus.generator import TestGenerator


def test_hephaestus_generates_and_runs_valid_test():
    """
    Integration test for the TestGenerator.

    This test verifies the full cycle:
    1. A simple function's source code is defined.
    2. TestGenerator creates a test script for it.
    3. The generated script is written to a temporary file.
    4. Pytest is executed on that file.
    5. The test asserts that pytest exited with a success code, proving
       the generated test is valid and passes.
    """
    # Arrange: Define a simple function and instantiate the generator.
    source_code = "def subtract(a, b):\n    return a - b"
    generator = TestGenerator()

    # Act: Generate the test code from the source string.
    generated_test_code = generator.generate(source_code)

    # Assert basic correctness of the generated string.
    assert "import pytest" in generated_test_code
    assert "def test_subtract_placeholder():" in generated_test_code
    assert source_code in generated_test_code

    # Arrange for dynamic execution: Write the generated code to a temp file.
    # Using a .py extension is important for pytest to discover it.
    temp_test_filename = "tests/temp_generated_test.py"
    try:
        with open(temp_test_filename, "w") as f:
            f.write(generated_test_code)

        # Act: Run pytest on the newly created file.
        # We use pytest.main() which returns an exit code. 0 means success.
        # Using '-q' for quiet mode to keep the test logs clean.
        exit_code = pytest.main([temp_test_filename, "-q"])

        # Assert: The exit code must be 0, indicating the test passed.
        assert exit_code == 0, "The pytest execution of the generated test failed."

    finally:
        # Clean up the temporary file regardless of the test outcome.
        if os.path.exists(temp_test_filename):
            os.remove(temp_test_filename)
