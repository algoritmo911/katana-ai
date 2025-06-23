import openai # type: ignore
import os
import logging
from typing import AsyncIterator, List, Dict, Optional

from .base_nlp_client import (
    AbstractLLMClient,
    NLPAPIError,
    NLPAuthenticationError,
    NLPBadRequestError,
    NLPInternalServerError,
    NLPRateLimitError,
    NLPServiceError,
)

logger = logging.getLogger(__name__)

# OpenAI Specific Exceptions
class OpenAIClientError(NLPServiceError):
    """Base exception for all OpenAI client errors."""
    pass

class OpenAIAPIError(OpenAIClientError, NLPAPIError):
    """Generic OpenAI API error."""
    pass

class OpenAIAuthenticationError(OpenAIClientError, NLPAuthenticationError):
    """Raised for OpenAI authentication failures."""
    pass

class OpenAIRateLimitError(OpenAIClientError, NLPRateLimitError):
    """Raised for OpenAI rate limit errors."""
    pass

class OpenAIInvalidRequestError(OpenAIClientError, NLPBadRequestError):
    """Raised for invalid requests to the OpenAI API."""
    pass

class OpenAIInternalServerError(OpenAIClientError, NLPInternalServerError):
    """Raised for OpenAI internal server errors."""
    pass


class OpenAIClient(AbstractLLMClient):
    """
    Client for interacting with the OpenAI API.
    """
    DEFAULT_MODEL = "gpt-3.5-turbo"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        effective_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not effective_api_key:
            raise OpenAIAuthenticationError(user_message="OpenAI API key is missing. Provide it via constructor or OPENAI_API_KEY env var.")

        self.api_key = effective_api_key
        self.model = model or self.DEFAULT_MODEL

        try:
            self.async_client = openai.AsyncOpenAI(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI AsyncClient: {e}", exc_info=True)
            raise OpenAIClientError(
                user_message="Failed to initialize OpenAI client during construction.",
                original_error=e
            )

    def _map_openai_error(self, e: openai.APIError) -> NLPServiceError:
        """Maps OpenAI API errors to custom NLPServiceError exceptions."""
        if isinstance(e, openai.AuthenticationError):
            return OpenAIAuthenticationError(user_message="OpenAI authentication failed. Check API key.", original_error=e)
        if isinstance(e, openai.RateLimitError):
            return OpenAIRateLimitError(user_message="OpenAI rate limit exceeded.", original_error=e)
        if isinstance(e, openai.BadRequestError):
            error_message = "OpenAI received a bad request."
            if hasattr(e, 'message') and e.message:
                error_message = f"OpenAI received a bad request: {e.message}"
            elif hasattr(e, 'body') and e.body and 'message' in e.body:
                 error_message = f"OpenAI received a bad request: {e.body['message']}"
            return OpenAIInvalidRequestError(user_message=error_message, original_error=e)
        if isinstance(e, openai.InternalServerError):
            return OpenAIInternalServerError(user_message="OpenAI internal server error.", original_error=e)
        if isinstance(e, openai.APIConnectionError):
            return NLPAPIError(user_message="Failed to connect to OpenAI API.", original_error=e)
        return OpenAIAPIError(user_message=f"An unexpected API error occurred with OpenAI: {str(e)}", original_error=e)

    def _prepare_messages(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if history:
            for item in history:
                if isinstance(item, dict) and "role" in item and "content" in item:
                    messages.append(item)
                else:
                    logger.warning(f"Skipping invalid history item: {item}")
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate_response(self, prompt: str, history: Optional[List[Dict[str, str]]] = None, **kwargs) -> str:
        messages = self._prepare_messages(prompt, history) # Corrected this line
        model_to_use = kwargs.pop("model", self.model)

        try:
            logger.debug(f"Sending request to OpenAI. Model: {model_to_use}. Messages: {messages}. Params: {kwargs}")
            completion = await self.async_client.chat.completions.create(
                model=model_to_use,
                messages=messages, # type: ignore[arg-type]
                **kwargs
            )
            response_content = completion.choices[0].message.content
            if response_content is None:
                raise OpenAIAPIError("Received null content from OpenAI without explicit error.")
            logger.debug(f"Received response from OpenAI: {response_content[:100]}...")
            return response_content
        except openai.APIError as e:
            logger.error(f"OpenAI API error in generate_response (model: {model_to_use}): {e}", exc_info=True)
            raise self._map_openai_error(e)
        except Exception as e:
            logger.error(f"Unexpected error in generate_response for OpenAI (model: {model_to_use}): {e}", exc_info=True)
            raise OpenAIClientError(user_message="An unexpected error occurred while generating OpenAI response.", original_error=e)

    async def stream_response(
        self, prompt: str, history: Optional[List[Dict[str, str]]] = None, **kwargs
    ) -> AsyncIterator[str]:
        messages = self._prepare_messages(prompt, history)
        model_to_use = kwargs.pop("model", self.model)

        try:
            logger.debug(f"Streaming request to OpenAI. Model: {model_to_use}. Messages: {messages}. Params: {kwargs}")
            stream = await self.async_client.chat.completions.create(
                model=model_to_use,
                messages=messages, # type: ignore[arg-type]
                stream=True,
                **kwargs
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content is not None:
                    yield content
            logger.debug(f"Finished streaming response from OpenAI for model {model_to_use}")
        except openai.APIError as e:
            logger.error(f"OpenAI API error during streaming (model: {model_to_use}): {e}", exc_info=True)
            raise self._map_openai_error(e)
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI streaming (model: {model_to_use}): {e}", exc_info=True)
            raise OpenAIClientError(user_message="An unexpected error occurred during OpenAI streaming.", original_error=e)

if __name__ == '__main__':
    import asyncio
    from dotenv import load_dotenv # type: ignore
    load_dotenv()

    logging.basicConfig(
        level=logging.DEBUG, # Changed to DEBUG to see more info from tests
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    logging.getLogger("openai").setLevel(logging.INFO) # Quieter OpenAI logs unless specifically debugging it
    logger.info("Starting OpenAIClient tests in __main__...")

    async def main_test():
        logger.info("Async main_test started.")
        openai_api_key_env = os.getenv("OPENAI_API_KEY")

        if not openai_api_key_env or openai_api_key_env == "YOUR_OPENAI_API_KEY" or openai_api_key_env == "dummy_openai_key":
            logger.warning("OPENAI_API_KEY not found, is a placeholder, or dummy. Skipping API interaction tests.")
        else:
            client = OpenAIClient(api_key=openai_api_key_env)
            logger.info(f"OpenAIClient initialized with API key from env for model {client.model}")

            logger.info("\n--- Testing generate_response ---")
            try:
                response = await client.generate_response(
                    "Hello, OpenAI! Tell me a short joke.",
                    model="gpt-3.5-turbo" # Explicitly using a common model
                )
                logger.info(f"OpenAI Response: {response}")
            except NLPServiceError as e:
                logger.error(f"OpenAI generate_response Error: {e.user_message}", exc_info=True)
                if e.original_error: logger.error(f"  Original error details: {e.original_error}")
            except Exception as e:
                logger.error(f"An unexpected error occurred during generate_response test: {e}", exc_info=True)

            logger.info("\n--- Testing stream_response ---")
            try:
                logger.info("OpenAI Streamed Response (gpt-3.5-turbo):")
                full_streamed_response = []
                async for chunk in client.stream_response(
                    "Write a short poem about coding. Just the poem.",
                    model="gpt-3.5-turbo" # Explicitly using a common model
                ):
                    print(chunk, end="", flush=True)
                    full_streamed_response.append(chunk)
                print("\n--- Stream finished ---")
                logger.info(f"Full streamed response collected: {''.join(full_streamed_response)[:200]}...") # Log more of the response
            except NLPServiceError as e:
                logger.error(f"\nOpenAI stream_response Error: {e.user_message}", exc_info=True)
                if e.original_error: logger.error(f"  Original error details: {e.original_error}")
            except Exception as e:
                logger.error(f"\nAn unexpected error occurred during stream_response test: {e}", exc_info=True)

            logger.info("\n--- Testing Authentication Error (with bad key) ---")
            bad_client = OpenAIClient(api_key="sk-thisisdefinitelynotarealkey12345")
            try:
                await bad_client.generate_response("This request should fail due to invalid authentication.")
                logger.error("  Test FAILED: Auth error test did not raise expected OpenAIAuthenticationError.")
            except OpenAIAuthenticationError as e:
                logger.info(f"  Test SUCCEEDED: Caught expected auth error: {e.user_message}")
            except NLPServiceError as e:
                logger.warning(f"  Test CAUTION: Caught NLPServiceError (expected OpenAIAuthenticationError, got {type(e).__name__}): {e.user_message}")
            except Exception as e:
                logger.error(f"  Test FAILED: Unexpected error during auth test: {type(e).__name__} - {e}", exc_info=True)

        logger.info("\n--- Testing Missing API Key on Instantiation ---")
        original_env_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            OpenAIClient(api_key=None)
            logger.error("  Test FAILED: OpenAIAuthenticationError NOT raised when API key is missing from both args and env.")
        except OpenAIAuthenticationError as e:
            logger.info(f"  Test SUCCEEDED: Caught expected missing API key error on instantiation: {e.user_message}")
        except Exception as e:
            logger.error(f"  Test FAILED: Unexpected error during missing API key instantiation test: {type(e).__name__} - {e}", exc_info=True)
        finally:
            if original_env_key is not None:
                os.environ["OPENAI_API_KEY"] = original_env_key
            elif "OPENAI_API_KEY" in os.environ :
                 del os.environ["OPENAI_API_KEY"]

        logger.info("\nOpenAIClient tests finished.")

    if __name__ == '__main__':
        logger.info("Running asyncio.run(main_test())")
        asyncio.run(main_test())
        logger.info("Finished asyncio.run(main_test())")
