import os
from unittest.mock import patch, MagicMock
import pytest
from katana.services.vectorization import VectorizationService

@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
def test_init_success():
    """Test successful initialization of VectorizationService."""
    with patch('katana.services.vectorization.openai.OpenAI') as mock_openai_client:
        service = VectorizationService()
        assert service.client is not None
        mock_openai_client.assert_called_once_with(api_key="test_key")

@patch.dict(os.environ, {"OPENAI_API_KEY": ""})
def test_init_failure_missing_key(caplog):
    """Test initialization failure when OPENAI_API_KEY is not set."""
    with caplog.at_level("WARNING"):
        service = VectorizationService()
        assert service.client is None
        assert "OPENAI_API_KEY environment variable not set" in caplog.text

@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
def test_init_failure_openai_exception(caplog):
    """Test initialization failure when openai.OpenAI raises an exception."""
    with patch('katana.services.vectorization.openai.OpenAI', side_effect=Exception("API Error")):
        with caplog.at_level("ERROR"):
            service = VectorizationService()
            assert service.client is None
            assert "Failed to initialize OpenAI client: API Error" in caplog.text

@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
def test_vectorize_success():
    """Test successful vectorization of text."""
    with patch('katana.services.vectorization.openai.OpenAI') as mock_openai_client:
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1, 0.2, 0.3]
        mock_response = MagicMock()
        mock_response.data = [mock_embedding]
        mock_openai_client.return_value.embeddings.create.return_value = mock_response

        service = VectorizationService()
        embedding = service.vectorize("test text")

        assert embedding == [0.1, 0.2, 0.3]
        mock_openai_client.return_value.embeddings.create.assert_called_once_with(
            input=["test text"], model="text-embedding-ada-002"
        )

def test_vectorize_uninitialized_client(caplog):
    """Test vectorization with an uninitialized client."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        with caplog.at_level("ERROR"):
            service = VectorizationService()
            result = service.vectorize("test text")
            assert result is None
            assert "OpenAI client not initialized. Cannot vectorize text." in caplog.text

@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
def test_vectorize_api_error(caplog):
    """Test handling of an error from the OpenAI API."""
    with patch('katana.services.vectorization.openai.OpenAI') as mock_openai_client:
        mock_openai_client.return_value.embeddings.create.side_effect = Exception("API Error")
        with caplog.at_level("ERROR"):
            service = VectorizationService()
            result = service.vectorize("test text")
            assert result is None
            assert "An error occurred while vectorizing text: API Error" in caplog.text
