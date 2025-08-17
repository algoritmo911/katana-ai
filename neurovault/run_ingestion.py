import sys
import os

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from neurovault.database import get_db_session
from neurovault.graph_database import get_graph_driver
from neurovault.pipelines.ingestion import IngestionOrchestrator

# Define the path to the source documents.
# This assumes the script is run from the `neurovault` directory.
SOURCE_DOCS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../sapiens_notes_private')
)


def main():
    """
    Main entry point to run the full document ingestion pipeline.
    """
    print("--- NeuroVault Ingestion Runner ---")

    db_session = None
    graph_driver = None

    try:
        # Get database connections
        db_session_generator = get_db_session()
        db_session = next(db_session_generator)
        graph_driver = get_graph_driver()

        if db_session is None or graph_driver is None:
            print("Error: Could not establish database connections.")
            return

        # Initialize and run the pipeline
        orchestrator = IngestionOrchestrator(db_session, graph_driver)
        orchestrator.run_pipeline(SOURCE_DOCS_PATH)

    except Exception as e:
        print(f"A critical error occurred during the ingestion pipeline: {e}")
        # In a real app, you might want more specific error handling.
        # For example, catching model download errors, db connection errors, etc.
    finally:
        # Clean up connections
        if db_session:
            db_session.close()
        if graph_driver:
            graph_driver.close()
        print("\n--- Ingestion Runner Finished ---")


if __name__ == "__main__":
    main()
