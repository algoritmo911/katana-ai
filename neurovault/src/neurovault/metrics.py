from prometheus_client import Counter, Histogram

# --- Ingestion Metrics ---

DOCUMENTS_INGESTED = Counter(
    'katana_documents_ingested_total',
    'Total number of documents processed by the ingestion pipeline',
    ['source']  # Label to distinguish different sources, e.g., 'local_filesystem'
)

INGESTION_DURATION = Histogram(
    'katana_ingestion_duration_seconds',
    'Time taken to ingest a single document',
    ['source']
)

# --- RAG Retrieval Metrics ---

RAG_QUERY_LATENCY = Histogram(
    'katana_rag_query_latency_seconds',
    'Latency of queries to the RAG retrieval service'
)

RAG_QUERY_ERRORS = Counter(
    'katana_rag_query_errors_total',
    'Total number of errors during RAG query processing'
)
