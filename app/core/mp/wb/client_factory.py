from __future__ import annotations

from typing import Dict, Tuple, TYPE_CHECKING, Callable, Awaitable, Optional

import httpx

from app.core.mp.wb.adapters.auth_client_mixin import AdapterAuthClient
from app.core.mp.wb.tokens.token_manager import TokenManager
from app.core.mp.wb.tokens.token_manager_factory import TokenManagerFactory

if TYPE_CHECKING:
    # Only import generated client for type checking, avoid circular dependencies
    # during runtime imports
    from app.core.mp.wb.adapters.promotion.v1.client import Client as PromotionClientV1


class ClientFactory:
    """Factory for creating and configuring API clients per shop_id and API section/version."""

    def __init__(self, token_manager_factory: TokenManagerFactory, 
                 async_http_clients: Dict[str, httpx.AsyncClient]) -> None:
        self._token_manager_factory = token_manager_factory
        self._async_http_clients = async_http_clients
        self._clients_cache: Dict[Tuple[str, str, int], AdapterAuthClient] = {}

    def get_client(self, shop_id: str, section: str, version: int) -> AdapterAuthClient:
        key = (shop_id, section, version)
        if key in self._clients_cache:
            return self._clients_cache[key]

        client = self._create_client(shop_id, section, version)
        self._clients_cache[key] = client
        return client

    def _create_client(self, shop_id: str, section: str, version: int) -> AdapterAuthClient:
        token_manager = self._token_manager_factory.get_manager(shop_id)
        async_client = self._async_http_clients.get(section)

        if async_client is None:
            raise ValueError(f"No httpx.AsyncClient configured for section {section}")

        # Dynamically import the correct generated client based on section and version
        if section == "promotion":
            if version == 1:
                from app.core.mp.wb.adapters.promotion.v1.client import Client as GeneratedClient
            else:
                raise ValueError(f"Unsupported promotion API version: {version}")
        else:
            raise ValueError(f"Unsupported API section: {section}")

        # Create an authenticated client instance
        base_url = async_client.base_url  # Assuming base_url is set on the AsyncClient
        # Generated client expects a string for base_url
        client: AdapterAuthClient = GeneratedClient(base_url=str(base_url), client=async_client)

        # Wire token management to the client
        def token_invalid_callback(token: Optional[str]) -> Awaitable[None]:
            # This callback will be called when the client determines a token is invalid
            return token_manager.mark_invalid(section, token)

        client.set_token(token_manager.get_token(section))
        client.set_token_invalid_callback(token_invalid_callback)
        client.set_async_httpx_client(async_client)

        return client


def get_client_factory(token_manager_factory: TokenManagerFactory, 
                       async_http_clients: Dict[str, httpx.AsyncClient]) -> ClientFactory:
    """Singleton accessor for ClientFactory."""
    # This function will be replaced by DI container wiring
    return ClientFactory(token_manager_factory, async_http_clients)


