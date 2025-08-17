from langchain.text_splitter import RecursiveCharacterTextSplitter
from dataclasses import dataclass

from neurovault.connectors.local_files import Document


@dataclass
class TextChunk:
    """A data class for a single chunk of text from a document."""
    parent_document_id: str
    text: str
    metadata: dict


class TextProcessor:
    """
    Processes raw text from documents into structured, bite-sized chunks.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initializes the TextProcessor with a text splitter.

        Args:
            chunk_size: The target size for each text chunk (in characters).
            chunk_overlap: The number of characters to overlap between chunks.
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    def split_document(self, document: Document) -> list[TextChunk]:
        """
        Splits a single document into a list of text chunks.
        """
        chunks = self.text_splitter.split_text(document.content)

        processed_chunks = []
        for i, chunk_text in enumerate(chunks):
            chunk = TextChunk(
                parent_document_id=document.id,
                text=chunk_text,
                metadata={
                    "chunk_number": i,
                    "total_chunks": len(chunks)
                }
            )
            processed_chunks.append(chunk)

        print(f"Split document '{document.id}' into {len(processed_chunks)} chunks.")
        return processed_chunks

    def extract_entities(self, text: str) -> list[dict]:
        """
        Placeholder for Named Entity Recognition (NER).
        In a real implementation, this would use a library like SpaCy or an
        NLP model to find entities like people, places, and organizations.
        """
        # This is a placeholder and will be implemented in a later stage.
        print("NER placeholder: No entities extracted.")
        return []
