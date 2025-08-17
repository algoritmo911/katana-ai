import sys
import os

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from neurovault.database import get_db_session
from neurovault.adapters.vector_db_adapter import VectorDBAdapter


def main():
    """
    Initializes the database schema for NeuroVault.
    - Creates the pgvector extension.
    - Creates the tables defined in the ORM models.
    """
    print("--- Running NeuroVault Database Initializer ---")

    # The get_db_session function is a generator, so we use `next` to get the session.
    db_session_generator = get_db_session()
    db_session = next(db_session_generator)

    if db_session is None:
        print("Error: Could not establish a database session.")
        return

    try:
        adapter = VectorDBAdapter(db_session)
        adapter.init_db()
    except Exception as e:
        print(f"An error occurred during database initialization: {e}")
    finally:
        # It's important to close the session.
        db_session.close()
        print("--- Database Initializer Finished ---")


if __name__ == "__main__":
    main()
