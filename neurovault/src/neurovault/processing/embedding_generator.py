from sentence_transformers import SentenceTransformer
from .text_processor import TextChunk


class EmbeddingGenerator:
    """
    Generates vector embeddings for text chunks using a sentence-transformer model.
    """

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initializes the EmbeddingGenerator and loads the specified model.
        The model is downloaded from the Hugging Face Hub on first use.
        """
        try:
            print(f"Loading sentence-transformer model: {model_name}...")
            self.model = SentenceTransformer(model_name)
            print("Model loaded successfully.")
        except Exception as e:
            print(f"Error loading SentenceTransformer model: {e}")
            # This is a critical failure, so we should raise it.
            raise

    def generate_embeddings(self, chunks: list[TextChunk]) -> list[list[float]]:
        """
        Generates embeddings for a list of text chunks.

        Args:
            chunks: A list of TextChunk objects.

        Returns:
            A list of vector embeddings, where each embedding corresponds
            to a chunk in the input list.
        """
        if not chunks:
            return []

        texts_to_embed = [chunk.text for chunk in chunks]

        print(f"Generating embeddings for {len(texts_to_embed)} text chunks...")
        embeddings = self.model.encode(texts_to_embed, show_progress_bar=False)
        print("Embedding generation complete.")

        # The model returns numpy arrays, so we convert them to plain lists of floats.
        return [embedding.tolist() for embedding in embeddings]

    def generate_embedding_for_query(self, query: str) -> list[float]:
        """
        Generates a single embedding for a query string.
        """
        if not query:
            return []

        embedding = self.model.encode(query, show_progress_bar=False)
        return embedding.tolist()

    def get_embedding_dimensions(self) -> int:
        """
        Returns the embedding dimensions of the loaded model.
        """
        return self.model.get_sentence_embedding_dimension()
