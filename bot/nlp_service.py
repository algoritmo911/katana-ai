import openai
import os
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure OpenAI API key
# It's good practice to load the API key from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY environment variable not set. NLP functionality will be limited.")
    # Depending on the desired behavior, you might raise an error here or allow the module to load
    # For now, we'll allow it to load but API calls will fail.
openai.api_key = OPENAI_API_KEY

# Define specific OpenAI exceptions we might want to retry on
RETRYABLE_EXCEPTIONS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.InternalServerError,
    # openai.APIStatusError, # Potentially retry on 5xx errors, but be cautious
)

DEFAULT_FALLBACK_RESPONSE = "I'm currently unable to process your request with the AI model. Please try again later."

class NLPService:
    def __init__(self, default_model="gpt-3.5-turbo"):
        self.default_model = default_model

    @retry(
        stop=stop_after_attempt(3),  # Retry up to 3 times
        wait=wait_exponential(multiplier=1, min=4, max=10),  # Exponential backoff
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        reraise=True # Reraise the exception if all retries fail
    )
    async def get_chat_completion(self, prompt: str, model: str = None) -> str:
        """
        Gets a chat completion from an OpenAI model with retry logic.
        """
        if not openai.api_key:
            logger.error("OpenAI API key is not configured. Cannot make API calls.")
            # Fallback if API key is missing
            return "NLP service is not configured. Please contact support."

        current_model = model if model else self.default_model
        logger.info(f"Requesting chat completion from {current_model} for prompt: '{prompt[:50]}...'")

        try:
            # Note: Ensure you are using the correct client and method for your openai library version
            # For openai >= 1.0.0
            client = openai.AsyncOpenAI(api_key=openai.api_key)
            response = await client.chat.completions.create(
                model=current_model,
                messages=[{"role": "user", "content": prompt}]
            )
            # Correctly access the content of the message
            content = response.choices[0].message.content.strip()
            logger.info(f"Received response from {current_model}: '{content[:50]}...'")
            return content
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI AuthenticationError: {e}. Check your API key and organization.")
            # This error is critical and non-retryable by just retrying the call
            return "Authentication with NLP service failed. Please check configuration."
        except openai.NotFoundError as e:
            logger.error(f"OpenAI NotFoundError (e.g. model not found): {e}. Model: {current_model}")
            return f"The specified AI model ({current_model}) was not found. Please check the model name."
        except openai.BadRequestError as e:
            logger.error(f"OpenAI BadRequestError: {e}. Prompt: '{prompt}'")
            # This usually means an issue with the prompt or request structure, not typically retryable
            return "There was an issue with the request to the AI model (e.g., invalid input)."
        except Exception as e:
            # This will catch exceptions from tenacity if all retries fail for RETRYABLE_EXCEPTIONS
            # or any other unexpected OpenAI error or general exception during the call.
            logger.error(f"Error during OpenAI API call to {current_model} for prompt '{prompt[:50]}...': {e}", exc_info=True)
            # Fallback response after retries or for non-retryable operational errors
            return DEFAULT_FALLBACK_RESPONSE

    async def get_anthropic_completion(self, prompt: str, model: str = "claude-2") -> str:
        """
        Placeholder for Anthropic API call with similar error handling.
        This needs to be implemented if Anthropic is a requirement.
        """
        logger.info(f"Anthropic call requested for model {model} with prompt: '{prompt[:50]}...'")
        # TODO: Implement Anthropic API call, retry logic, and specific error handling
        # from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT (or their new SDK)
        # ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
        # if not ANTHROPIC_API_KEY:
        #     logger.error("ANTHROPIC_API_KEY not set.")
        #     return "Anthropic NLP service is not configured."
        # client = Anthropic(api_key=ANTHROPIC_API_KEY)
        # try:
        #     completion = await client.completions.create( # or messages.create for new SDK
        #         model=model,
        #         max_tokens_to_sample=300,
        #         prompt=f"{HUMAN_PROMPT} {prompt}{AI_PROMPT}",
        #     )
        #     return completion.completion
        # except Exception as e:
        #     logger.error(f"Error during Anthropic API call: {e}", exc_info=True)
        #     return DEFAULT_FALLBACK_RESPONSE
        return f"Anthropic provider not yet implemented. Fallback for: '{prompt[:30]}...'"

# Example usage (optional, for testing this module directly)
if __name__ == '__main__':
    import asyncio

    async def main():
        # To test this, you'll need to set your OPENAI_API_KEY environment variable
        if not OPENAI_API_KEY:
            print("Please set the OPENAI_API_KEY environment variable to test.")
            return

        nlp = NLPService()

        print("\n--- Testing OpenAI Chat Completion ---")
        # Test with a valid prompt
        response_openai = await nlp.get_chat_completion("Hello, who are you?")
        print(f"OpenAI Response: {response_openai}")

        # Test with a potentially problematic model (if it doesn't exist or you don't have access)
        # response_openai_bad_model = await nlp.get_chat_completion("Test prompt", model="gpt-nonexistent-model")
        # print(f"OpenAI Response (bad model): {response_openai_bad_model}")

        # Test Anthropic (will return placeholder)
        print("\n--- Testing Anthropic Chat Completion (Placeholder) ---")
        response_anthropic = await nlp.get_anthropic_completion("Hello, Anthropic!")
        print(f"Anthropic Response: {response_anthropic}")

    # Python 3.7+
    asyncio.run(main())
