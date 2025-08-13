import os
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Use a secure way to get the API token from environment variables
# This should be set in your production environment.
# For local development, you can use a .env file.
API_TOKEN = os.getenv("KATANA_API_TOKEN")

# We instantiate the HTTPBearer scheme.
# "bearer" is the name of the scheme. It will be used in the OpenAPI docs.
bearer_scheme = HTTPBearer()

async def get_current_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    """
    Dependency to get and validate the bearer token.
    """
    if not API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API token not configured on the server."
        )

    # Use secrets.compare_digest to prevent timing attacks
    is_correct_token = secrets.compare_digest(credentials.credentials, API_TOKEN)

    if not is_correct_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials

# For now, we just validate the token. In the future, this could be expanded
# to look up a user associated with the token.
async def get_current_user_placeholder(token: str = Depends(get_current_token)):
    """
    A placeholder for a function that would fetch a user from the database
    based on the validated token. For now, it just returns a dummy user identifier.
    """
    return {"username": "katana_user"}

# This is the dependency that will be used in the endpoint decorators.
# It's an alias for clarity in the endpoint definitions.
# E.g., @router.get("/some-protected-route", dependencies=[Depends(api_key_auth)])
api_key_auth = Depends(get_current_token)
