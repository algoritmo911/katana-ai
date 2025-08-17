from sqlalchemy.orm import Session
from neo4j import Driver

from neurovault.connectors.local_files import LocalFileConnector
from neurovault.metrics import DOCUMENTS_INGESTED, INGESTION_DURATION
from neurovault.processing.text_processor import TextProcessor
from neurovault.processing.embedding_generator import EmbeddingGenerator
from neurovault.adapters.vector_db_adapter import VectorDBAdapter
from neurovault.adapters.graph_db_adapter import GraphDBAdapter


class IngestionOrchestrator:
    """
    Orchestrates the entire document ingestion pipeline.
    """

    def __init__(self, db_session: Session, graph_driver: Driver):
        # Initialize all components of the pipeline
        self.text_processor = TextProcessor()
        self.embedding_generator = EmbeddingGenerator()

        # Initialize database adapters
        self.vector_db_adapter = VectorDBAdapter(db_session)
        self.graph_db_adapter = GraphDBAdapter(graph_driver)

    def run_pipeline(self, source_path: str):
        """
        Executes the full ingestion pipeline for a given source directory.

        1. Scans for documents.
        2. For each document:
           a. Adds a node to the graph database.
           b. Splits the document into text chunks.
           c. Generates vector embeddings for the chunks.
           d. Saves the chunks and their embeddings to the vector database.
        """
        print("\n--- Starting Ingestion Pipeline ---")

        # 1. Scan for documents
        file_connector = LocalFileConnector(source_path)
        documents = file_connector.get_documents()

        if not documents:
            print("No new documents found to ingest.")
            print("--- Ingestion Pipeline Finished ---")
            return

        for doc in documents:
            with INGESTION_DURATION.labels(source='local_filesystem').time():
                print(f"\nProcessing document: {doc.id}")

                # 2a. Add document node to the graph DB
                self.graph_db_adapter.add_document(doc.id, doc.metadata)

                # 2b. Split document into chunks
                chunks = self.text_processor.split_document(doc)
                if not chunks:
                    continue

                # 2c. Generate embeddings for the chunks
                embeddings = self.embedding_generator.generate_embeddings(chunks)

                # Prepare data for batch saving
                embedding_batch = []
                for i, chunk in enumerate(chunks):
                    embedding_batch.append({
                        "source_document_id": chunk.parent_document_id,
                        "text_chunk": chunk.text,
                        "embedding": embeddings[i]
                    })

                # 2d. Save chunks and embeddings to the vector DB
                self.vector_db_adapter.save_embeddings(embedding_batch)

            # Increment the counter after successful processing of a document
            DOCUMENTS_INGESTED.labels(source='local_filesystem').inc()

        print("\n--- Ingestion Pipeline Finished Successfully ---")
