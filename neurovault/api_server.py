import sys
import os
import structlog
from flask import Flask, request, jsonify
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from neurovault.metrics import RAG_QUERY_LATENCY, RAG_QUERY_ERRORS
from neurovault.logging_config import configure_logging

# Configure logging as the first step
configure_logging()
log = structlog.get_logger()

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from neurovault.database import get_db_session
from neurovault.pipelines.retrieval import RAGQueryService

app = Flask(__name__)

# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

# It's not ideal to initialize the service here in a real app,
# but for this simple case it's sufficient. A real app would use a
# proper application factory pattern.
db_session_generator = get_db_session()
db_session = next(db_session_generator)
rag_service = RAGQueryService(db_session, logger=log)


@app.before_request
def before_request():
    # This function runs before each request.
    # We clear the contextvars to ensure no data leaks between requests.
    structlog.contextvars.clear_contextvars()

    # Extract trace ID from header and bind it to the logger context for this request.
    trace_id = request.headers.get("X-Trace-ID")
    if trace_id:
        structlog.contextvars.bind_contextvars(trace_id=trace_id)


@app.route('/retrieve', methods=['POST'])
@RAG_QUERY_LATENCY.time() # This decorator measures the latency of the endpoint
def retrieve():
    """
    API endpoint to retrieve context for a given query.
    Expects a JSON payload with a "query" key.
    """
    request_log = log.bind(endpoint="/retrieve", method="POST")

    data = request.get_json()
    if not data or "query" not in data:
        request_log.error("request_validation_failed", reason="Missing 'query' in body")
        RAG_QUERY_ERRORS.inc()
        return jsonify({"error": "Missing 'query' in request body"}), 400

    query = data["query"]
    request_log.info("context_retrieval_started", query=query)

    try:
        context = rag_service.retrieve_context(query)
        request_log.info("context_retrieval_succeeded")
        return jsonify({"context": context})
    except Exception as e:
        request_log.exception("context_retrieval_failed")
        RAG_QUERY_ERRORS.inc()
        return jsonify({"error": "An internal error occurred"}), 500


def main():
    # In the docker-compose setup, a proper WSGI server like Gunicorn
    # would be used to run this application.
    # This main function is for local testing.
    log.info("--- NeuroVault API Server Starting ---", host="0.0.0.0", port=5001)
    app.run(host='0.0.0.0', port=5001)


if __name__ == '__main__':
    main()
