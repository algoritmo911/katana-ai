import unittest
from unittest.mock import patch, AsyncMock
import aiohttp

# Assuming GemmaInterface is in src.interfaces.gemma_interface
# Adjust import path if necessary based on how tests are run (e.g., if src is in PYTHONPATH)
from ..gemma_interface import GemmaInterface

class TestGemmaInterface(unittest.IsolatedAsyncioTestCase):

    def test_init_success(self):
        """Test successful initialization."""
        api_key = "test_api_key"
        interface = GemmaInterface(api_key=api_key)
        self.assertEqual(interface.api_key, api_key)
        self.assertEqual(interface.endpoint, "https://api.kodjima.com/v1/query")

    def test_init_custom_endpoint(self):
        """Test initialization with a custom endpoint."""
        api_key = "test_api_key"
        custom_endpoint = "http://localhost:8080/test_query"
        interface = GemmaInterface(api_key=api_key, api_endpoint=custom_endpoint)
        self.assertEqual(interface.endpoint, custom_endpoint)

    def test_init_no_api_key(self):
        """Test initialization failure without API key."""
        with self.assertRaisesRegex(ValueError, "API key is required for GemmaInterface."):
            GemmaInterface(api_key="")

    async def test_receive_passthrough(self):
        """Test that receive() returns the payload as is."""
        interface = GemmaInterface(api_key="test_key")
        test_payload = {"data": "test_data", "user": "test_user"}
        received_context = await interface.receive(test_payload)
        self.assertEqual(received_context, test_payload)

        received_none = await interface.receive(None) # Test with Optional payload
        self.assertIsNone(received_none)


    @patch('aiohttp.ClientSession.post', new_callable=AsyncMock)
    async def test_send_successful_request(self, mock_post):
        """Test send() makes a correct POST request and handles successful response."""
        api_key = "test_api_key_send"
        endpoint = "https://fakeapi.kodjima.com/v1/test_query"
        interface = GemmaInterface(api_key=api_key, api_endpoint=endpoint)

        # Mock the response from session.post(..).async_with.__aenter__()
        mock_response = mock_post.return_value.__aenter__.return_value
        mock_response.status = 200
        mock_response.raise_for_status = unittest.mock.Mock() # Does nothing if status is 200
        # mock_response.json = AsyncMock(return_value={"result": "success"}) # If we were processing json

        test_request_data = {"query": "Hello Gemma?", "user_id": "123"}

        await interface.send(test_request_data)

        # Verify that session.post was called correctly
        mock_post.assert_called_once_with(
            endpoint,
            json=test_request_data,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        mock_response.raise_for_status.assert_called_once()

    @patch('aiohttp.ClientSession.post', new_callable=AsyncMock)
    async def test_send_http_error(self, mock_post):
        """Test send() handles HTTP errors by raising them."""
        api_key = "test_api_key_error"
        endpoint = "https://fakeapi.kodjima.com/v1/error_query"
        interface = GemmaInterface(api_key=api_key, api_endpoint=endpoint)

        # Configure the mock response to simulate an HTTP error
        mock_response = mock_post.return_value.__aenter__.return_value
        mock_response.status = 500
        # Create an exception instance similar to what aiohttp would raise
        http_error = aiohttp.ClientResponseError(
            request_info=unittest.mock.Mock(),
            history=unittest.mock.Mock(),
            status=500,
            message="Internal Server Error"
        )
        mock_response.raise_for_status = unittest.mock.Mock(side_effect=http_error)

        test_request_data = {"query": "This will fail"}

        with self.assertRaises(aiohttp.ClientResponseError) as cm:
            await interface.send(test_request_data)

        self.assertEqual(cm.exception, http_error) # Check if the same exception is propagated

        mock_post.assert_called_once_with(
            endpoint,
            json=test_request_data,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        mock_response.raise_for_status.assert_called_once()

    @patch('aiohttp.ClientSession.post', new_callable=AsyncMock)
    async def test_send_client_error_generic(self, mock_post):
        """Test send() handles generic aiohttp.ClientError."""
        api_key = "test_api_key_client_error"
        interface = GemmaInterface(api_key=api_key)

        # Configure post to raise a generic ClientError (e.g., connection issue)
        generic_client_error = aiohttp.ClientError("Generic network issue")
        mock_post.side_effect = generic_client_error

        test_request_data = {"query": "Network error test"}

        with self.assertRaises(aiohttp.ClientError) as cm:
            await interface.send(test_request_data)

        self.assertEqual(cm.exception, generic_client_error)
        mock_post.assert_called_once_with(
            interface.endpoint, # Default endpoint
            json=test_request_data,
            headers={"Authorization": f"Bearer {api_key}"}
        )

if __name__ == '__main__':
    unittest.main()
