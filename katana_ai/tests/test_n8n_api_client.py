import pytest
import respx
import json
from httpx import Response
from katana_ai.adapters.n8n_api_client import N8nApiClient

# --- Constants for Testing ---
TEST_URL = "http://localhost:5678"
TEST_API_KEY = "test-key"
TEST_WORKFLOW_ID = "123"
BASE_API_URL = f"{TEST_URL}/api/v1"

@pytest.fixture
def client():
    """Provides a test instance of the N8nApiClient."""
    return N8nApiClient(n8n_url=TEST_URL, api_key=TEST_API_KEY)

def test_client_initialization():
    """Tests successful client initialization."""
    client = N8nApiClient(n8n_url=TEST_URL, api_key=TEST_API_KEY)
    assert client.n8n_url == TEST_URL
    assert client.api_key == TEST_API_KEY
    assert client.base_url == BASE_API_URL

def test_client_initialization_missing_url_raises_error():
    """Tests that missing URL raises a ValueError."""
    with pytest.raises(ValueError, match="n8n URL must be provided"):
        N8nApiClient(n8n_url=None, api_key=TEST_API_KEY)

def test_client_initialization_missing_key_raises_error():
    """Tests that missing API key raises a ValueError."""
    with pytest.raises(ValueError, match="n8n API key must be provided"):
        N8nApiClient(n8n_url=TEST_URL, api_key=None)

@pytest.mark.asyncio
@respx.mock
async def test_get_workflow_success(client):
    """Tests successful retrieval of a single workflow."""
    mock_response = {"id": TEST_WORKFLOW_ID, "name": "Test Workflow"}
    route = respx.get(f"{BASE_API_URL}/workflows/{TEST_WORKFLOW_ID}").mock(return_value=Response(200, json=mock_response))

    workflow = await client.get_workflow(TEST_WORKFLOW_ID)

    assert route.called
    assert workflow == mock_response

@pytest.mark.asyncio
@respx.mock
async def test_update_workflow_success(client):
    """Tests successful update of a workflow."""
    workflow_data = {"nodes": [], "connections": {}}
    mock_response = {"message": "Workflow updated successfully"}
    route = respx.put(f"{BASE_API_URL}/workflows/{TEST_WORKFLOW_ID}").mock(return_value=Response(200, json=mock_response))

    response = await client.update_workflow(TEST_WORKFLOW_ID, workflow_data)

    assert route.called
    assert response == mock_response
    # Verify that the request payload was correct
    assert json.loads(route.calls.last.request.content) == workflow_data

@pytest.mark.asyncio
@respx.mock
async def test_api_error_raises_exception(client):
    """Tests that a 404 Not Found error raises an exception."""
    from httpx import HTTPStatusError
    route = respx.get(f"{BASE_API_URL}/workflows/not-found").mock(return_value=Response(404))

    with pytest.raises(HTTPStatusError):
        await client.get_workflow("not-found")

@pytest.mark.asyncio
@respx.mock
async def test_activate_workflow_success(client):
    """Tests successful activation of a workflow."""
    mock_response = {"message": "Workflow activated"}
    route = respx.post(f"{BASE_API_URL}/workflows/{TEST_WORKFLOW_ID}/activate").mock(return_value=Response(200, json=mock_response))

    response = await client.activate_workflow(TEST_WORKFLOW_ID)

    assert route.called
    assert response == mock_response

@pytest.mark.asyncio
@respx.mock
async def test_get_executions_success(client):
    """Tests successful retrieval of workflow executions."""
    mock_response = [{"id": "exec1", "finished": True}]
    route = respx.get(f"{BASE_API_URL}/executions?workflowId={TEST_WORKFLOW_ID}&limit=50").mock(return_value=Response(200, json=mock_response))

    executions = await client.get_executions(TEST_WORKFLOW_ID)

    assert route.called
    assert executions == mock_response
