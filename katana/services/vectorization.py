import os
import logging
from typing import List, Optional

import openai

# Initialize logger
logger = logging.getLogger(__name__)

class VectorizationService:
    """
    A service to handle the vectorization of text using an embedding model.
    """
    def __init__(self):
        """
        Initializes the VectorizationService.
        It retrieves the OpenAI API key from environment variables.
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY environment variable not set. VectorizationService will not be functional.")
            self.client = None
        else:
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
                self.client = None

    def vectorize(self, text: str, model: str = "text-embedding-ada-002") -> Optional[List[float]]:
        """
        Generates a vector embedding for the given text.

        Args:
            text: The text to vectorize.
            model: The name of the embedding model to use.

        Returns:
            A list of floats representing the vector embedding, or None if an error occurs.
        """
        if not self.client:
            logger.error("OpenAI client not initialized. Cannot vectorize text.")
            return None

        try:
            # Replace newlines with spaces, as recommended by OpenAI for embedding quality
            text = text.replace("\n", " ")
            response = self.client.embeddings.create(input=[text], model=model)
            embedding = response.data[0].embedding
            logger.debug(f"Successfully vectorized text. Embedding dimension: {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"An error occurred while vectorizing text: {e}", exc_info=True)
            return None
