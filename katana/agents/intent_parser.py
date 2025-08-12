"""
This module defines the IntentParser agent, responsible for converting
natural language text into a structured IntentContract.
"""
from pydantic import ValidationError
from katana.core.praetor.intent.contract import IntentContract


class IntentParser:
    """
    An AI agent that parses natural language into a formal IntentContract.

    This agent uses a Large Language Model (LLM) with a constrained output
    schema to ensure the generated contract is always valid.
    """

    def __init__(self, llm_client):
        """
        Initializes the IntentParser.

        Args:
            llm_client: A client for interacting with a Large Language Model.
                        It is expected to have a method `generate_structured_output`
                        that returns a dictionary.
        """
        self.llm_client = llm_client

    def parse(self, natural_language_input: str) -> IntentContract:
        """
        Parses a natural language string and returns a structured IntentContract.

        This method orchestrates the interaction with an LLM and validates
        the output to ensure it conforms to the IntentContract schema.

        Args:
            natural_language_input: The user's request in plain text.

        Returns:
            A validated instance of IntentContract.

        Raises:
            IntentParsingError: If the LLM output fails validation against the
                                IntentContract schema.
        """
        # In a real implementation, a more complex prompt would be constructed.
        prompt = (
            f"Parse the following user request into a structured JSON object "
            f"based on the provided schema. The request is: "
            f"'{natural_language_input}'"
        )

        # The llm_client is expected to return a dictionary.
        # In a real scenario, this client would handle the API call and retry logic.
        llm_response_data = self.llm_client.generate_structured_output(
            prompt=prompt,
            response_schema=IntentContract.model_json_schema()
        )

        try:
            # Validate the dictionary and create a Pydantic model instance
            intent_contract = IntentContract.model_validate(llm_response_data)
            return intent_contract
        except ValidationError as e:
            # If validation fails, raise a custom error with structured details.
            raise IntentParsingError(
                "Failed to validate the LLM response against the IntentContract schema.",
                details=e.errors()
            ) from e


class IntentParsingError(Exception):
    """Custom exception for errors during intent parsing."""
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details
