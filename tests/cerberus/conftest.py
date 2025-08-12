import pytest
from pydantic import BaseModel, Field, ValidationError


# 1. Define a fake Pydantic contract to be used for the test pipeline.
# This contract is simple but has enough variety to test the system.
class FakeCommandContract(BaseModel):
    """A fake command contract for testing the Inquisitor pipeline."""
    item_id: int = Field(..., gt=0, description="The ID of the item.")
    item_name: str = Field(..., min_length=1, max_length=10, description="The name of the item.")
    is_enabled: bool = Field(True, description="A boolean flag.")


# 2. Define a mock Response class.
# The generated tests expect a response object with a 'status_code'.
class MockResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code

    def json(self):
        # A dummy json method in case the test tries to access the body
        return {}


# 3. Define the mock 'client' fixture.
# This is the most critical part of the meta-test setup.
# It simulates the behavior of a web framework's test client.
@pytest.fixture
def client():
    """A mock client that simulates API requests for the generated tests."""
    class MockClient:
        def post(self, endpoint: str, json: dict):
            """
            Simulates a POST request.
            It validates the payload against the FakeCommandContract and returns
            a mock response with status 200 for valid data or 422 for invalid data.
            """
            try:
                # Attempt to validate the incoming JSON data using the fake contract.
                # This is the core of the simulation.
                FakeCommandContract.model_validate(json)
                # If validation is successful, return a success response.
                return MockResponse(status_code=200)
            except ValidationError:
                # If Pydantic raises a validation error, return the 422 error code.
                return MockResponse(status_code=422)

    return MockClient()
