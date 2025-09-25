from __future__ import annotations

from typing import Any, Dict, Optional


class AuthenticatedClient:
    """A thin wrapper over httpx.AsyncClient that carries authentication token and fixed settings.

    Instances are created by AuthenticatedClientFactory and used for single request context.
    """

    def __init__(self, base_url: str, token: Optional[str] = None) -> None:
        self.base_url = base_url
        self.token = token

    async def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Perform a request using underlying httpx client. Implementation provided later."""
        raise NotImplementedError


class BaseAdapter:
    """Base class for stateful adapters scoped by (shop_id, section, version).

    Adapters should use an AuthenticatedClient factory to obtain per-request clients.
    """

    def __init__(self, shop_id: str, section: str, version: str) -> None:
        self.shop_id = shop_id
        self.section = section
        self.version = version

    async def close(self) -> None:
        """Optional cleanup for adapter resources."""
        pass

    # Example of a wrapped call signature that concrete adapters will implement
    async def call_method(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """Generic method placeholder to be implemented by concrete adapters."""
        raise NotImplementedError
