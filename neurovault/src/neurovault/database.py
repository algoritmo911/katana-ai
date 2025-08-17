import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Get the database URL from environment variables.
# The default value is for local testing if the env var is not set.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://user:pass@localhost:5432/db"
)

# The engine is the entry point to the database.
engine = create_engine(DATABASE_URL)

# The SessionLocal class is a factory for creating new Session objects.
# These sessions are the primary interface for all database operations.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is a factory for creating base classes for our ORM models.
Base = declarative_base()


def get_db_session():
    """
    Dependency function to get a database session.
    Ensures that the database connection is always closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
