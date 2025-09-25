from __future__ import annotations

from typing import Any, Callable, Coroutine
import asyncio


class _TemporaryAuthenticatedClient:
    """Lightweight holder for per-request auth client. The real httpx client
    is injected via `session` attribute by the caller (shared singleton).
    """

    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url
        self.token = token
        self.session = None  # to be set to shared httpx.AsyncClient

    def attach_session(self, session: Any) -> None:
        self.session = session


def _is_auth_error(resp: Any) -> bool:
    status = getattr(resp, "status_code", None)
    return status in (401, 403)


def auth_decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator that injects a per-request AuthenticatedClient built on top of
    a shared httpx.AsyncClient (in DI). If the request returns 401/403 it will
    mark the token invalid and retry once.
    """

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not args:
            return await func(*args, **kwargs)

        self = args[0]
        token_manager = getattr(self, "token_manager", None)
        client_factory = getattr(self, "authenticated_client_factory", None)
        shared_client = getattr(self, "http_client", None)

        if token_manager is None or client_factory is None:
            return await func(*args, **kwargs)

        # obtain token and create temporary client
        token = await token_manager.get_token(self.section)
        temp_client = client_factory(self.section, token)
        # attach shared httpx AsyncClient session for actual transport
        if shared_client is not None and hasattr(temp_client, "attach_session"):
            temp_client.attach_session(shared_client)

        # attach temporary client onto self for the duration of the call
        setattr(self, "_authenticated_client", temp_client)

        try:
            resp = await func(*args, **kwargs)
        finally:
            # cleanup attribute to avoid leaking per-request client
            try:
                delattr(self, "_authenticated_client")
            except Exception:
                pass

        # on auth failure, mark invalid and retry once
        if _is_auth_error(resp):
            try:
                token_manager.mark_invalid(self.section)
            except Exception:
                pass
            # get new token and retry once
            new_token = await token_manager.get_token(self.section)
            temp_client = client_factory(self.section, new_token)
            if shared_client is not None and hasattr(temp_client, "attach_session"):
                temp_client.attach_session(shared_client)
            setattr(self, "_authenticated_client", temp_client)
            try:
                return await func(*args, **kwargs)
            finally:
                try:
                    delattr(self, "_authenticated_client")
                except Exception:
                    pass

        return resp

    return wrapper
