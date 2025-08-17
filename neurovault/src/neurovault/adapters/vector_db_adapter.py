from sqlalchemy.orm import Session
from sqlalchemy import text

from neurovault.database import Base, engine
from neurovault.models import VectorEmbedding


class VectorDBAdapter:
    """
    Adapter for all interactions with the vector database (PostgreSQL + pgvector).
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def init_db(self):
        """
        Initializes the database. Creates the pgvector extension and all tables.
        This is an idempotent operation.
        """
        print("Initializing vector database...")
        # Create the pgvector extension if it doesn't exist.
        self.db.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
        # Create all tables defined by the Base metadata.
        Base.metadata.create_all(bind=engine)
        self.db.commit()
        print("Vector database initialization complete.")

    def save_embeddings(self, batch: list[dict]):
        """
        Saves a batch of embeddings to the database.

        Args:
            batch: A list of dictionaries, where each dictionary contains:
                   'source_document_id' (str),
                   'text_chunk' (str),
                   'embedding' (list[float]).
        """
        if not batch:
            return

        new_embeddings = [VectorEmbedding(**item) for item in batch]
        self.db.add_all(new_embeddings)
        self.db.commit()
        print(f"Successfully saved {len(new_embeddings)} embeddings to the database.")

    def find_similar(self, query_vector: list[float], top_k: int = 5) -> list[VectorEmbedding]:
        """
        Finds the most similar text chunks for a given query vector.

        Args:
            query_vector: The vector representation of the user's query.
            top_k: The number of similar items to return.

        Returns:
            A list of VectorEmbedding objects, ordered by similarity.
        """
        if not query_vector:
            return []

        # pgvector offers three operators for similarity search:
        # <-> : Euclidean distance
        # <#> : Negative inner product
        # <=> : Cosine distance (1 - cosine similarity)
        # We use cosine distance as it's effective for semantic similarity.
        results = self.db.query(VectorEmbedding).order_by(
            VectorEmbedding.embedding.l2_distance(query_vector)
        ).limit(top_k).all()

        return results
