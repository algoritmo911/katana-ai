import os
from google import generativeai as genai
from .base_nlp_client import BaseNLPClient, NLPAPIError, NLPAuthenticationError, NLPInternalServerError

# Attempt to load the google.generativeai module and handle potential import errors
try:
    import google.generativeai as genai
    GOOGLE_GENERATIVEAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENERATIVEAI_AVAILABLE = False
    # You could log this warning or handle it as appropriate for your application
    # print("Warning: google.generativeai module not found. GemmaClient will not be usable.")


class GemmaClient(BaseNLPClient):
    def __init__(self, api_key: str = None, model_name: str = "gemini-1.0-pro", **kwargs):
        super().__init__(api_key=api_key, model_name=model_name, **kwargs)

        if not GOOGLE_GENERATIVEAI_AVAILABLE:
            raise ImportError("The 'google-generativeai' package is required to use GemmaClient. Please install it.")

        self.api_key = api_key or os.getenv("GEMMA_API_KEY")
        if not self.api_key:
            raise NLPAuthenticationError("Gemma API key not provided. Set GEMMA_API_KEY environment variable or pass it as an argument.")

        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name) # Use self.model_name from super
        except Exception as e:
            # This could be due to various reasons, e.g., invalid API key format, network issues during configuration
            raise NLPAuthenticationError(f"Failed to configure Gemma client with API key: {e}", original_error=e)


    def generate_text(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7, **kwargs) -> str:
        """
        Generates text using the Gemma API.

        Args:
            prompt: The prompt to send to the API.
            max_tokens: The maximum number of tokens to generate.
            temperature: The temperature to use for generation.

        Returns:
            The generated text.
        """
        try:
            # Note: Gemma's API uses 'generation_config' for parameters like max_tokens and temperature.
            # 'max_output_tokens' is the equivalent of max_tokens.
            # 'temperature' is directly supported.
            if not GOOGLE_GENERATIVEAI_AVAILABLE:
                raise RuntimeError("GemmaClient cannot generate text because 'google-generativeai' is not installed.")

            # Ensure model is initialized
            if not hasattr(self, 'model') or self.model is None:
                # This might happen if __init__ failed silently or was bypassed.
                raise NLPInternalServerError("Gemma model not initialized. Configuration might have failed.")

            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                # You can add other parameters from kwargs if Gemma API supports them
                # For example: top_p=kwargs.get('top_p'), top_k=kwargs.get('top_k')
            )

            # Filter kwargs to only pass supported ones if necessary, or pass all if API handles extras
            # For now, only using max_tokens and temperature explicitly via GenerationConfig
            response = self.model.generate_content(prompt, generation_config=generation_config)

            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            else:
                # Handle cases where the response might be blocked or empty
                block_reason = "Unknown reason"
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    block_reason = response.prompt_feedback.block_reason.name
                # Consider raising a specific error or returning a structured response
                raise NLPAPIError(f"No content generated. Block reason: {block_reason}. Check safety ratings or prompt.")

        except genai.types.BlockedPromptException as bpe:
            # More specific handling for blocked prompts
            raise NLPAPIError(f"Prompt blocked by Gemma API: {bpe}", original_error=bpe)
        except (NLPInternalServerError, RuntimeError) as internal_err:
            # Allow specific internal/runtime errors (raised before API call) to propagate
            raise internal_err
        except Exception as e:
            # Catch other exceptions, likely from the genai library during API call
            # print(f"Error generating text with Gemma: {e}")
            raise NLPAPIError(f"Gemma API call failed: {e}", original_error=e)

    def close(self):
        """
        Closes the Gemma client.
        The google-generativeai library does not seem to require explicit session closing
        for simple API calls. This method is for interface consistency.
        """
        # No specific close action needed for genai client as per current library usage
        # print("GemmaClient closed.") # Optional: for debugging or logging if needed
        pass

# Example usage (for testing or manual runs, ensure GEMMA_API_KEY is set)
if __name__ == '__main__':
    if not GOOGLE_GENERATIVEAI_AVAILABLE:
        print("Cannot run GemmaClient example: google-generativeai library is not installed.")
    else:
        try:
            # Requires GEMMA_API_KEY to be set in the environment
            client = GemmaClient(model_name="gemini-pro") # gemini-1.0-pro might be more specific

            print(f"Using model: {client.model_name}")

            prompts = [
                "Translate the following English text to French: 'Hello, world!'",
                "Write a short python function to calculate factorial.",
                "What is the capital of France?",
                # "A more complex query requiring analysis: Given the recent trends in renewable energy, what are the key challenges for solar panel adoption in urban areas?"
            ]

            for p in prompts:
                print(f"\nPrompt: {p}")
                try:
                    generated_text = client.generate_text(p, max_tokens=150, temperature=0.6)
                    print(f"Generated Text: {generated_text}")
                except NLPAPIError as e:
                    print(f"API Error: {e}")
                except Exception as e:
                    print(f"An unexpected error occurred: {e}")

            client.close()

        except NLPAuthenticationError as auth_err:
            print(auth_err)
        except ImportError as imp_err:
            print(imp_err)
        except Exception as e:
            print(f"An unexpected error occurred during setup: {e}")
