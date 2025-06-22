import os
import anthropic # Assuming this is the synchronous client
from anthropic import AsyncAnthropic # Importing the async client

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    print("Warning: ANTHROPIC_API_KEY environment variable not set. Anthropic functionality will be disabled.")

# Initialize the async client only if the API key is available
client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

async def generate_text_anthropic(prompt: str, model: str = "claude-2") -> str | None:
    """
    Generates text using the Anthropic API.
    """
    if not client:
        print("Error: Anthropic client not initialized. Cannot generate text.")
        return None
    try:
        # Using the async client, so await the call
        response = await client.messages.create(
            model=model,
            max_tokens=1024, # Default max_tokens, can be parameterized
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        # Process content from potentially list of content blocks
        if response.content and isinstance(response.content, list):
            # Assuming text content is the primary type we're interested in
            text_parts = [block.text for block in response.content if hasattr(block, 'text')]
            return " ".join(text_parts) if text_parts else None
        elif hasattr(response, 'text'): # For older versions or different response structures
             return response.text
        return None # Or handle as an error if content is not as expected
    except Exception as e:
        print(f"Error generating text with Anthropic: {e}")
        return None
