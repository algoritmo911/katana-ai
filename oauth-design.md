# Centralized OAuth Server Design

## Overview

This document outlines the design for a centralized OAuth server to manage Google authentication for all services.

## Architecture

The OAuth server will be a standalone service responsible for the following:

*   **Handling the OAuth 2.0 flow with Google.** This includes redirecting users to Google for authentication, handling the callback from Google, and obtaining access and refresh tokens.
*   **Storing tokens securely.** Tokens will be encrypted and stored in a database (Postgres or Redis).
*   **Providing an API for services to obtain tokens.** Services will be able to request tokens from the OAuth server using a secure API.
*   **Refreshing tokens automatically.** The OAuth server will automatically refresh expired access tokens using the refresh token.

## API

The OAuth server will expose the following API endpoints:

*   `POST /oauth/token`: This endpoint will be used by services to request an access token. The service will need to provide a valid API key to access this endpoint.
*   `POST /oauth/refresh`: This endpoint will be used to refresh an access token.

## Security

*   All communication with the OAuth server will be over HTTPS.
*   The token database will be encrypted.
*   Services will need to use an API key to access the OAuth server's API.
*   The OAuth server will be protected by a firewall.

## Token Refreshing

The OAuth server will be responsible for automatically refreshing expired access tokens. This will be done using a CRON job that runs periodically and checks for expired tokens. When an expired token is found, the OAuth server will use the refresh token to obtain a new access token from Google. The new access token will then be stored in the database, replacing the old one.

## Integration Plan

This section outlines the plan for integrating the centralized OAuth server with existing services.

### Katana AI

The Katana AI service will be modified to use the centralized OAuth server instead of local API keys. This will involve the following changes:

*   The code that currently uses Google API keys will be modified to call the OAuth server's API to obtain an access token.
*   The access token will be stored in memory and used to make requests to the Google API.
*   If the access token expires, the Katana AI service will request a new one from the OAuth server.

### n8n

If n8n is being used, a custom node will be created to obtain access tokens from the OAuth server. This node will be used in n8n workflows to automate tasks that require access to the Google API.

### Other Services

Any other services that use the Google API will be modified in a similar way to the Katana AI service.
