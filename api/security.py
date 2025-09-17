import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Load the master API key from environment variables
# For a real production system, this might come from a more secure secret store.
MASTER_API_KEY = os.getenv("KATANA_API_KEY", "default_master_key")

async def get_api_key(api_key: str = Security(api_key_header)):
    """
    Dependency that checks for a valid API key in the request header.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An API key is required."
        )
    if api_key != MASTER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key."
        )
    return api_key
