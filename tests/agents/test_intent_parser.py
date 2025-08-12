"""
Unit tests for the IntentParser agent, covering various validation scenarios.
"""
import unittest
from unittest.mock import Mock
from katana.agents.intent_parser import IntentParser, IntentParsingError
from katana.core.praetor.intent.contract import IntentContract


class TestIntentParserExpanded(unittest.TestCase):
    """
    Expanded test suite for the IntentParser, focusing on validation logic.
    """

    def setUp(self):
        """
        Set up a mock LLM client before each test.
        """
        self.mock_llm_client = Mock()
        self.parser = IntentParser(llm_client=self.mock_llm_client)

    def _run_parse_with_data(self, data):
        """Helper method to run the parser with specific data."""
        self.mock_llm_client.generate_structured_output.return_value = data
        return self.parser.parse("A user request")

    def _expect_parsing_error(self, data, expected_type, expected_loc):
        """Helper method to assert that a specific IntentParsingError is raised."""
        with self.assertRaises(IntentParsingError) as cm:
            self._run_parse_with_data(data)

        error_details = cm.exception.details
        self.assertIsInstance(error_details, list)
        self.assertTrue(len(error_details) > 0)
        # Check if the expected error is in the list of errors
        found_error = False
        for error in error_details:
            if error.get('type') == expected_type and error.get('loc') == expected_loc:
                found_error = True
                break
        self.assertTrue(found_error, f"Expected error type '{expected_type}' at '{expected_loc}' not found.")

    def test_parse_success_full_data(self):
        """Test successful parsing with a complete and valid data structure."""
        valid_data = {
            "goal": "Increase user retention by 5%",
            "constraints": ["Budget under $10k", "No new infrastructure"],
            "success_criteria": ["5% increase in 30-day retention", "Validated by A/B test"]
        }
        contract = self._run_parse_with_data(valid_data)
        self.assertIsInstance(contract, IntentContract)
        self.assertEqual(contract.goal, valid_data["goal"])
        self.assertEqual(contract.constraints, valid_data["constraints"])
        self.assertEqual(contract.success_criteria, valid_data["success_criteria"])

    def test_parse_success_no_constraints(self):
        """Test successful parsing when the optional 'constraints' field is omitted."""
        valid_data = {
            "goal": "Deploy the new feature",
            "success_criteria": ["Feature is live"]
        }
        contract = self._run_parse_with_data(valid_data)
        self.assertIsInstance(contract, IntentContract)
        self.assertEqual(contract.goal, valid_data["goal"])
        self.assertEqual(contract.constraints, [])  # Should default to an empty list

    # --- Tests for new validation rules ---

    def test_parse_failure_empty_goal(self):
        """Test failure when 'goal' is an empty string."""
        invalid_data = {"goal": "", "success_criteria": ["Criterion"]}
        self._expect_parsing_error(invalid_data, 'string_too_short', ('goal',))

    def test_parse_failure_empty_success_criteria_list(self):
        """Test failure when 'success_criteria' is an empty list."""
        invalid_data = {"goal": "A goal", "success_criteria": []}
        self._expect_parsing_error(invalid_data, 'too_short', ('success_criteria',))

    def test_parse_failure_empty_string_in_success_criteria(self):
        """Test failure when an item in 'success_criteria' is an empty string."""
        invalid_data = {"goal": "A goal", "success_criteria": [""]}
        self._expect_parsing_error(invalid_data, 'string_too_short', ('success_criteria', 0))

    def test_parse_failure_empty_string_in_constraints(self):
        """Test failure when an item in 'constraints' is an empty string."""
        invalid_data = {"goal": "A goal", "constraints": [""], "success_criteria": ["Criterion"]}
        self._expect_parsing_error(invalid_data, 'string_too_short', ('constraints', 0))

    # --- Re-testing original failure cases ---

    def test_parse_failure_missing_goal(self):
        """Test parsing failure when the required 'goal' field is missing."""
        invalid_data = {"success_criteria": ["A criterion"]}
        self._expect_parsing_error(invalid_data, 'missing', ('goal',))

    def test_parse_failure_missing_success_criteria(self):
        """Test parsing failure when the required 'success_criteria' field is missing."""
        invalid_data = {"goal": "A goal"}
        self._expect_parsing_error(invalid_data, 'missing', ('success_criteria',))

    def test_parse_failure_incorrect_type_for_constraints(self):
        """Test parsing failure when 'constraints' has an incorrect data type."""
        invalid_data = {"goal": "A goal", "constraints": "not a list", "success_criteria": ["Criterion"]}
        self._expect_parsing_error(invalid_data, 'list_type', ('constraints',))

    def test_parse_failure_incorrect_item_type_for_success_criteria(self):
        """Test parsing failure when an item in 'success_criteria' is not a string."""
        invalid_data = {"goal": "A goal", "success_criteria": [123]}
        self._expect_parsing_error(invalid_data, 'string_type', ('success_criteria', 0))

    def test_parse_failure_extra_field(self):
        """Test parsing failure when the data contains an extra, forbidden field."""
        invalid_data = {"goal": "A goal", "success_criteria": ["Criterion"], "extra": "field"}
        self._expect_parsing_error(invalid_data, 'extra_forbidden', ('extra',))


if __name__ == '__main__':
    unittest.main()
