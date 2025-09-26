from typing import Optional

import httpx



class AdapterAuthClient:

    def __init__(token,)


    def with_headers(self, headers: dict[str, str]) -> None:
        raise RuntimeError('Not implemented, use "set_token" method instead')

    def with_cookies(self, cookies: dict[str, str]) -> None:
        raise RuntimeError('Not implemented, use "set_token" method instead')

    def with_timeout(self, timeout: httpx.Timeout) -> "SimpleAuthenticatedClient":
        raise RuntimeError('Not implemented, use "set_token" method instead')

    def set_token(self, token: str, prefix: Optional[str] = None) -> "SimpleAuthenticatedClient":
        """Меняем токен на лету"""
        self.token = token
        if prefix is not None:
            self.prefix = prefix
        auth_value = f"{self.prefix} {self.token}" if self.prefix else self.token
        self._headers[self.auth_header_name] = auth_value

        if self._client is not None:
            self._client.headers[self.auth_header_name] = auth_value
        if self._async_client is not None:
            self._async_client.headers[self.auth_header_name] = auth_value

        return self
