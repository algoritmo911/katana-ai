import os
import asyncio
from huggingface_hub import InferenceClient

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")

if not HUGGINGFACE_API_TOKEN:
    print("Warning: HUGGINGFACE_API_TOKEN environment variable not set. HuggingFace functionality will be disabled.")

# Initialize the client only if the API token is available
client = InferenceClient(token=HUGGINGFACE_API_TOKEN) if HUGGINGFACE_API_TOKEN else None

async def generate_text_huggingface(prompt: str, model: str = "gpt2") -> str | None:
    """
    Generates text using the HuggingFace Inference API.
    """
    if not client:
        print("Error: HuggingFace Inference client not initialized. Cannot generate text.")
        return None
    try:
        # Wrap the synchronous client call in asyncio.to_thread
        response = await asyncio.to_thread(
            client.text_generation,
            prompt,
            model=model,
            max_new_tokens=250
        )
        return response
    except Exception as e:
        print(f"Error generating text with HuggingFace: {e}")
        return None

async def text_to_image_huggingface(prompt: str, model: str = "stabilityai/stable-diffusion-2") -> bytes | None:
    """
    Generates an image using the HuggingFace Inference API for text-to-image models.
    """
    if not client:
        print("Error: HuggingFace Inference client not initialized. Cannot generate image.")
        return None
    try:
        # Wrap the synchronous client call in asyncio.to_thread
        image_bytes = await asyncio.to_thread(
            client.text_to_image,
            prompt,
            model=model
        )
        return image_bytes
    except Exception as e:
        print(f"Error generating image with HuggingFace: {e}")
        return None
