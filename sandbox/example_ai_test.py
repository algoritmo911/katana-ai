import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# Useful for local development and sandbox testing
load_dotenv()

# It's good practice to place imports of your bot's modules after .env loading,
# especially if they initialize clients using env vars at import time.
from bot.ai_providers.openai import generate_text_openai
from bot.ai_providers.anthropic import generate_text_anthropic
from bot.ai_providers.huggingface import generate_text_huggingface, text_to_image_huggingface

async def main():
    """
    An example script to test AI provider integrations.
    Ensure your API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, HUGGINGFACE_API_TOKEN)
    are set as environment variables or in a .env file in the project root.
    """
    print("--- Testing AI Providers ---")

    # Test OpenAI
    print("\nTesting OpenAI...")
    openai_prompt = "Explain the concept of asynchronous programming in Python in simple terms."
    openai_response = await generate_text_openai(openai_prompt, model="gpt-3.5-turbo")
    if openai_response:
        print(f"OpenAI Response:\n{openai_response}")
    else:
        print("Failed to get response from OpenAI.")

    # Test Anthropic
    print("\nTesting Anthropic...")
    anthropic_prompt = "What are some key benefits of using Claude AI?"
    # Ensure you use a model name that your Anthropic key has access to.
    # e.g., "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-2.1" etc.
    # The default "claude-2" in the function might be outdated for some keys.
    # Update generate_text_anthropic or pass model explicitly if needed.
    anthropic_response = await generate_text_anthropic(anthropic_prompt, model="claude-3-haiku-20240307") # Using a specific model
    if anthropic_response:
        print(f"Anthropic Response:\n{anthropic_response}")
    else:
        print("Failed to get response from Anthropic.")

    # Test HuggingFace Text Generation
    print("\nTesting HuggingFace Text Generation...")
    hf_text_prompt = "Write a short story about a robot learning to paint."
    hf_text_response = await generate_text_huggingface(hf_text_prompt, model="gpt2") # Default model is "gpt2"
    if hf_text_response:
        print(f"HuggingFace Text Response:\n{hf_text_response}")
    else:
        print("Failed to get response from HuggingFace (Text).")

    # Test HuggingFace Text-to-Image
    # Note: Text-to-image can be slow and might require specific model access.
    # This is commented out by default to prevent long waits or errors if not configured.
    # print("\nTesting HuggingFace Text-to-Image...")
    # hf_image_prompt = "A futuristic cityscape with flying cars, digital art style."
    # hf_image_bytes = await text_to_image_huggingface(hf_image_prompt, model="stabilityai/stable-diffusion-2")
    # if hf_image_bytes:
    #     with open("sandbox_generated_image.png", "wb") as f:
    #         f.write(hf_image_bytes)
    #     print("HuggingFace Image Response: Saved to sandbox_generated_image.png")
    # else:
    #     print("Failed to get response from HuggingFace (Image).")

    print("\n--- AI Provider Tests Complete ---")

if __name__ == "__main__":
    # Ensure API keys are loaded before running main
    # Example: set them in your shell or use a .env file
    # For .env, ensure python-dotenv is installed (added to requirements.txt)
    # and load_dotenv() is called at the start of the script.

    # Check for a key to give a hint if tests might fail
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("HUGGINGFACE_API_TOKEN"):
        print("Warning: No AI provider API keys found in environment variables.")
        print("Please set OPENAI_API_KEY, ANTHROPIC_API_KEY, and/or HUGGINGFACE_API_TOKEN to run tests.")

    asyncio.run(main())
