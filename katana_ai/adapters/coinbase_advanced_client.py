"""
Client for the Coinbase Advanced Trade API.

This module provides a client for interacting with the Coinbase Advanced Trade API.
It handles authentication, request signing, and error handling.
"""
import os
import time
import hmac
import hashlib
import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.coinbase.com"


class CoinbaseAPIError(Exception):
    """Base exception for Coinbase API errors."""
    pass


class CoinbaseForbiddenError(CoinbaseAPIError):
    """Raised for 403 Forbidden errors."""
    pass


class CoinbaseRateLimitError(CoinbaseAPIError):
    """Raised for 429 Too Many Requests errors."""
    pass


class CoinbaseInternalServerError(CoinbaseAPIError):
    """Raised for 500 Internal Server Error errors."""
    pass


class CoinbaseAdvancedClient:
    """
    A client for the Coinbase Advanced Trade API.
    """

    def __init__(self):
        """
        Initializes the client with API credentials from environment variables.
        """
        self.api_key = os.getenv("COINBASE_API_KEY")
        self.api_secret = os.getenv("COINBASE_API_SECRET")
        if not self.api_key or not self.api_secret:
            raise ValueError(
                "COINBASE_API_KEY and COINBASE_API_SECRET must be set in the environment."
            )
        self.client = httpx.AsyncClient(base_url=API_URL)

    def _sign_message(self, method: str, request_path: str, body: str = "") -> tuple[str, str]:
        """
        Signs the message for the API request.

        Args:
            method: The HTTP method.
            request_path: The request path.
            body: The request body.

        Returns:
            A tuple containing the timestamp and the signature.
        """
        timestamp = str(int(time.time()))
        message = f"{timestamp}{method.upper()}{request_path}{body}"
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return timestamp, signature

    def _get_auth_headers(self, method: str, request_path: str, body: str = "") -> dict:
        """
        Constructs the authentication headers for the API request.

        Args:
            method: The HTTP method.
            request_path: The request path.
            body: The request body.

        Returns:
            A dictionary containing the authentication headers.
        """
        timestamp, signature = self._sign_message(method, request_path, body)
        return {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json",
        }

    async def get_products(self):
        """
        Gets a list of available products.

        Returns:
            A dictionary containing the list of products.
        """
        request_path = "/api/v3/brokerage/products"
        headers = self._get_auth_headers("GET", request_path)
        try:
            response = await self.client.get(request_path, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise CoinbaseForbiddenError(f"Forbidden: {e.response.text}") from e
            if e.response.status_code == 429:
                raise CoinbaseRateLimitError(f"Rate limit exceeded: {e.response.text}") from e
            if e.response.status_code == 500:
                raise CoinbaseInternalServerError(f"Internal server error: {e.response.text}") from e
            raise CoinbaseAPIError(f"HTTP error: {e.response.text}") from e

    async def place_market_order(self, product_id: str, side: str, size: float):
        """
        [SANDBOX-ONLY] Places a mock market order.
        This is a placeholder for Phase 3 and does not execute real trades.
        """
        print(f"[Hephaestus SANDBOX] Mock market order: {side} {size} of {product_id}")
        # In a real implementation, this would make a POST request to the API.
        # For now, we just return a mock success response.
        return {
            "status": "SUCCESS",
            "order_id": f"mock-order-{int(time.time())}",
            "product_id": product_id,
            "side": side,
            "size": size
        }
