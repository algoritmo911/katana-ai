import os
from dotenv import load_dotenv

load_dotenv()

def get_secret(key: str) -> str:
    """
    Retrieves a secret from the environment variables.
    """
    return os.getenv(key)
