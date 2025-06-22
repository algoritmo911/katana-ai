import os
import openai
from openai import AsyncOpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY environment variable not set. OpenAI functionality will be disabled.")

# Initialize the async client
client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

async def generate_text_openai(prompt: str, model: str = "gpt-3.5-turbo") -> str | None:
    """
    Generates text using the OpenAI API.
    """
    if not client:
        print("Error: OpenAI client not initialized. Cannot generate text.")
        return None
    try:
        # Note: The openai library's client methods like create are already async-compatible
        # when the client is initialized with OpenAI(api_key=...) or AsyncOpenAI(api_key=...)
        # Forcing an `await` here if the client method isn't a coroutine might cause issues
        # depending on the exact version and how it handles async.
        # If using `openai.AsyncOpenAI`, then `await` is correct.
        # If using `openai.OpenAI` and its methods are not true async methods,
        # they might be blocking or need to be run in a thread pool executor for non-blocking behavior.
        # For now, assuming the library handles this gracefully or we switch to AsyncOpenAI.
        completion = await client.chat.completions.create( # Added await for AsyncOpenAI
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error generating text with OpenAI: {e}")
        return None

# Removed DUMMY_FUNCTION_FOR_TESTING_OPENAI as it's not needed for the actual implementation
