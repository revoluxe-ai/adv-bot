import ssl
from typing import Any, Optional, Protocol, Union

import httpx


class AuthenticatedClientProtocol(Protocol):
    """
    Протокол для аутентифицированного клиента, совместимого с httpx.Client и httpx.AsyncClient.
    """
    raise_on_unexpected_status: bool
    _base_url: str
    _cookies: dict[str, str]
    _headers: dict[str, str]
    _timeout: Optional[httpx.Timeout]
    _verify_ssl: Union[str, bool, ssl.SSLContext]
    _follow_redirects: bool
    _httpx_args: dict[str, Any]
    _client: Optional[httpx.Client]
    _async_client: Optional[httpx.AsyncClient]
    token: str
    prefix: str
    auth_header_name: str

    def with_headers(self, headers: dict[str, str]) -> "AuthenticatedClientProtocol": ...

    def with_cookies(self, cookies: dict[str, str]) -> "AuthenticatedClientProtocol": ...

    def with_timeout(self, timeout: httpx.Timeout) -> "AuthenticatedClientProtocol": ...

    def set_httpx_client(self, client: httpx.Client) -> "AuthenticatedClientProtocol": ...

    def get_httpx_client(self) -> httpx.Client: ...

    def __enter__(self) -> "AuthenticatedClientProtocol": ...

    def __exit__(self, *args: Any, **kwargs: Any) -> None: ...

    def set_async_httpx_client(self, async_client: httpx.AsyncClient) -> "AuthenticatedClientProtocol": ...

    def get_async_httpx_client(self) -> httpx.AsyncClient: ...

    async def __aenter__(self) -> "AuthenticatedClientProtocol": ...

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None: ...

    def set_new_token(self, token: str) -> None: ...
