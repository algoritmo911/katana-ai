import sys
import os

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from neurovault.graph_database import get_graph_driver
from neurovault.adapters.graph_db_adapter import GraphDBAdapter


def main():
    """
    A simple script to test the connection to Neo4j and the GraphDBAdapter.
    """
    print("--- Running NeuroVault Graph DB Test Script ---")

    driver = None
    try:
        # 1. Get the Neo4j driver
        driver = get_graph_driver()
        adapter = GraphDBAdapter(driver)

        # 2. Define some test data
        test_doc_id = "test_document_1.md"
        test_entity_name = "Katana Project"
        test_entity_type = "Project"

        # 3. Add a document and an entity
        print(f"Adding document: {test_doc_id}")
        adapter.add_document(test_doc_id, metadata={"source": "test_script"})

        print(f"Adding entity '{test_entity_name}' to document '{test_doc_id}'")
        adapter.add_entity(test_doc_id, test_entity_name, test_entity_type)

        # 4. Retrieve the entity to verify it was added
        print(f"Verifying entities for document: {test_doc_id}")
        entities = adapter.get_document_entities(test_doc_id)

        if entities and entities[0]['name'] == test_entity_name:
            print("SUCCESS: Found test entity linked to the document.")
            print(f"Retrieved data: {entities}")
        else:
            print(f"FAILURE: Could not find the test entity. Found: {entities}")

    except Exception as e:
        print(f"An error occurred during the test: {e}")
    finally:
        # 5. Close the driver connection
        if driver:
            driver.close()
        print("--- Graph DB Test Script Finished ---")


if __name__ == "__main__":
    main()
