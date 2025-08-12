import pytest
from pathlib import Path

# Import the core components of the Inquisitor system
from katana.testing.data_factory import DataFactory
from katana.testing.test_scribe import TestScribe

# Import the fake contract and mock client fixture defined in conftest.py
from tests.cerberus.conftest import FakeCommandContract


def test_inquisitor_pipeline(tmp_path: Path):
    """
    This is the meta-test. It validates the entire test generation pipeline.

    It performs the following steps:
    1. Dynamically creates test data for a fake command using DataFactory.
    2. Generates a complete pytest test file using TestScribe.
    3. Executes the generated test file using pytest.main().
    4. Asserts that all generated tests pass, proving the pipeline's integrity.
    """
    # 1. Instantiate DataFactory with the fake contract
    data_factory = DataFactory(FakeCommandContract)

    # 2. Generate test cases (using a smaller number for a quick meta-test)
    test_cases = data_factory.generate_test_cases(total_cases=20)

    # Sanity check: Ensure both valid and invalid data were generated
    has_valid = any(case['is_valid'] for case in test_cases)
    has_invalid = any(not case['is_valid'] for case in test_cases)
    assert has_valid, "DataFactory should have generated at least one valid case."
    assert has_invalid, "DataFactory should have generated at least one invalid case."

    # 3. Instantiate TestScribe with the contract and generated data
    scribe = TestScribe(contract_model=FakeCommandContract, test_cases=test_cases)

    # 4. Generate the test file content
    generated_code = scribe.generate_test_file_content()

    # 5. Write the generated code to a temporary file
    # The `tmp_path` fixture provides a temporary directory unique to this test run.
    generated_test_file = tmp_path / "test_generated_by_scribe.py"
    generated_test_file.write_text(generated_code)

    # 6. Create a self-contained test environment in the temporary directory
    # by writing the conftest file alongside the generated test file.
    # This ensures pytest can find the 'client' fixture.
    conftest_path = Path(__file__).parent / "conftest.py"
    (tmp_path / "conftest.py").write_text(conftest_path.read_text())

    # 7. Execute the generated tests using pytest.main()
    # We run pytest on the temporary directory. It will discover both the
    # generated test file and the conftest file.
    # The result is the exit code. 0 means all tests passed.
    result = pytest.main([str(generated_test_file)])

    # 8. Assert that the pytest run was successful
    assert result == pytest.ExitCode.OK, f"The pytest run on the generated file failed with exit code {result}."
