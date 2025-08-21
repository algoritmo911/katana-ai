# 0006. n8n REST API Client

*   **Status:** Accepted
*   **Date:** 2025-08-15

## Context

The project requires the ability to programmatically modify n8n workflows. Previous attempts to achieve this by directly manipulating the `workflow.json` file proved to be unreliable, fragile, and led to file corruption. This approach is not scalable or safe for autonomous operations.

A more robust, stable, and "surgical" method is needed to interact with n8n workflows, as outlined in the "Prometheus Unbound" directive.

## Decision

We will implement a dedicated, asynchronous Python client, `N8nApiClient`, to act as the sole interface for all interactions with the n8n REST API.

Key technical choices for this client are:
1.  **Library:** We will use `httpx` for handling asynchronous HTTP requests. It is a modern, well-supported library with an API that is highly compatible with the popular `requests` library.
2.  **Authentication:** Authentication will be performed by passing an API key in the `X-N8N-API-KEY` header, as specified in the official n8n documentation. The client will be initialized with the key, abstracting the authentication details away from the calling code.
3.  **Encapsulation:** The client will encapsulate all endpoint logic (e.g., `/api/v1/workflows/{id}`, `/api/v1/workflows/{id}/activate`). This makes the rest of the codebase cleaner, as it can call high-level methods like `client.update_workflow()` without needing to know the specific API routes or HTTP methods.
4.  **Error Handling:** The client will be responsible for basic HTTP error handling, raising exceptions for non-2xx responses to ensure that API failures are immediately and explicitly handled by the calling services.

## Consequences

### Positive

*   **Atomicity and Stability:** All workflow updates are now atomic operations sent to the n8n server. The server itself validates the payload, which prevents the kind of file corruption experienced previously.
*   **Maintainability:** Centralizing API interaction logic into a single client makes the code easier to manage, debug, and extend.
*   **Testability:** The client can be easily unit-tested by mocking the HTTP requests, ensuring its reliability.
*   **Foundation for Autonomy:** This client is the fundamental building block for all future autonomous capabilities outlined in the project roadmap, including the Synthesis and Feedback layers.

### Negative

*   **New Dependency:** Introduces a dependency on the `httpx` library.
*   **Configuration Overhead:** Requires the n8n instance URL and a valid API key to be configured in the environment where the agent operates. The API must be enabled on the n8n server.
