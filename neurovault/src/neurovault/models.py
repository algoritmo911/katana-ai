import uuid
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from .database import Base


class VectorEmbedding(Base):
    """
    SQLAlchemy model for storing text chunks and their vector embeddings.
    """
    __tablename__ = "vector_embeddings"

    # A unique identifier for the embedding record.
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # A reference to the source document, e.g., a file path or a URL.
    source_document_id = Column(String, nullable=False, index=True)

    # The actual text chunk that has been embedded.
    text_chunk = Column(Text, nullable=False)

    # The vector representation of the text_chunk.
    # The dimensions of the vector (e.g., 1536 for OpenAI's text-embedding-ada-002)
    # should match the model being used. We'll assume 1536 for now.
    embedding = Column(Vector(1536), nullable=False)

    def __repr__(self):
        return f"<VectorEmbedding(id={self.id}, source='{self.source_document_id}')>"
