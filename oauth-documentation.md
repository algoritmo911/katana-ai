# OAuth Server Documentation

This document provides documentation for the centralized OAuth server.

## Overview

The centralized OAuth server is a standalone service that manages Google authentication for all services. It handles the OAuth 2.0 flow with Google, stores tokens securely, and provides an API for services to obtain tokens.

## Architecture

The OAuth server is a standalone service built with FastAPI. It is responsible for the following:

*   **Handling the OAuth 2.0 flow with Google.** This includes redirecting users to Google for authentication, handling the callback from Google, and obtaining access and refresh tokens.
*   **Storing tokens securely.** Tokens are encrypted and stored in a database (Postgres or Redis).
*   **Providing an API for services to obtain tokens.** Services can request tokens from the OAuth server using a secure API.
*   **Refreshing tokens automatically.** The OAuth server automatically refreshes expired access tokens using the refresh token.

## API Reference

The OAuth server exposes the following API endpoints:

*   `POST /oauth/token`: This endpoint is used by services to request an access token. The service will need to provide a valid API key to access this endpoint.
*   `POST /oauth/refresh`: This endpoint is used to refresh an access token.

## Getting Started

To use the OAuth server, you will need to do the following:

1.  Obtain an API key from the OAuth server administrator.
2.  Modify your service to call the OAuth server's API to obtain an access token.
3.  Use the access token to make requests to the Google API.

## Instructions for the Team

This section provides instructions for the team on how to use the new OAuth system.

### Obtaining an API Key

To obtain an API key for the OAuth server, please contact the administrator.

### Using the OAuth API

To use the OAuth API, you will need to make a POST request to the `/oauth/token` endpoint. The request should include your API key in the `Authorization` header.

### Example

Here is an example of how to obtain an access token using Python:

```python
import requests

api_key = "YOUR_API_KEY"

headers = {
    "Authorization": f"Bearer {api_key}"
}

response = requests.post("http://localhost:8000/oauth/token", headers=headers)

if response.status_code == 200:
    print("Successfully obtained token:")
    print(response.json())
else:
    print("Error obtaining token:")
    print(response.text)
```

## Support

If you have any questions or problems, please contact the OAuth server administrator.
