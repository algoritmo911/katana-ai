import structlog
from sqlalchemy.orm import Session

from neurovault.adapters.vector_db_adapter import VectorDBAdapter
from neurovault.processing.embedding_generator import EmbeddingGenerator


class RAGQueryService:
    """
    Handles the retrieval part of the Retrieval-Augmented Generation pipeline.
    """

    def __init__(self, db_session: Session, logger=None):
        """
        Initializes the service with a database session and a logger.
        """
        self.db_session = db_session
        self.vector_db_adapter = VectorDBAdapter(self.db_session)
        self.log = logger or structlog.get_logger()

        # It's important to reuse the same embedding model for queries and documents.
        self.embedding_generator = EmbeddingGenerator()

    def retrieve_context(self, query: str, top_k: int = 5) -> str:
        """
        Retrieves the most relevant text chunks from the database for a given query.

        Args:
            query: The natural language query from the user.
            top_k: The maximum number of context chunks to retrieve.

        Returns:
            A single string containing the concatenated text of the most
            relevant chunks, which will be used as context for an LLM.
        """
        log = self.log.bind(query=query, top_k=top_k)
        log.info("retrieving_context")

        # 1. Generate an embedding for the query.
        query_embedding = self.embedding_generator.generate_embedding_for_query(query)

        if not query_embedding:
            log.warn("query_embedding_failed", reason="Generator returned empty list.")
            return ""

        # 2. Find similar document chunks in the vector database.
        similar_embeddings = self.vector_db_adapter.find_similar(
            query_vector=query_embedding,
            top_k=top_k
        )

        if not similar_embeddings:
            log.info("no_relevant_context_found")
            return ""

        # 3. Format the retrieved chunks into a single context string.
        context_parts = []
        sources = []
        for embedding in similar_embeddings:
            context_parts.append(
                f"Source: {embedding.source_document_id}\n"
                f"Content: {embedding.text_chunk}"
            )
            sources.append(embedding.source_document_id)

        context_string = "\n\n---\n\n".join(context_parts)
        log.info(
            "context_retrieval_successful",
            retrieved_chunks=len(similar_embeddings),
            source_documents=sources
        )

        return context_string
