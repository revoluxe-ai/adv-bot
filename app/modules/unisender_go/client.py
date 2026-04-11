from __future__ import annotations

import json
import logging

import httpx
from pydantic import ValidationError

from app.modules.unisender_go.exceptions import UnisenderGoError
from app.modules.unisender_go.schemas import (
    EmailSendApiRequest,
    EmailSendErrorBody,
    EmailSendResponse,
    TransactionalMessage,
)
from app.settings.settings_master import Settings

logger = logging.getLogger(__name__)

_DEFAULT_BASE = "https://goapi.unisender.ru/ru/transactional/api/v1"


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


class UnisenderGoClient:
    """Async client for Unisender Go transactional Web API (``email/send.json``)."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE,
        timeout_sec: float = 30.0,
        default_from_email: str | None = None,
        default_global_language: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Unisender Go API key must be non-empty")
        self._api_key = api_key
        self._base_url = _normalize_base_url(base_url)
        self._timeout_sec = timeout_sec
        self._default_from_email = default_from_email
        self._default_global_language = default_global_language
        self._http = http_client
        self._owns_client = http_client is None

    @classmethod
    def from_settings(cls, settings: Settings) -> UnisenderGoClient:
        key = settings.unisender_go_api_key
        if not key:
            raise ValueError(
                "UNISENDER_GO_API_KEY is not set; configure Unisender Go in the environment",
            )
        return cls(
            key,
            base_url=settings.unisender_go_api_base,
            timeout_sec=float(settings.unisender_go_request_timeout_sec),
            default_from_email=settings.unisender_go_default_from_email,
            default_global_language=settings.unisender_go_default_global_language,
        )

    async def __aenter__(self) -> UnisenderGoClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client and self._http is not None:
            await self._http.aclose()
            self._http = None

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self._timeout_sec)
        return self._http

    def _merge_defaults(self, message: TransactionalMessage) -> TransactionalMessage:
        data = message.model_dump(exclude_none=True)
        if not data.get("from_email") and self._default_from_email:
            data["from_email"] = self._default_from_email
        if not data.get("global_language") and self._default_global_language:
            data["global_language"] = self._default_global_language
        return TransactionalMessage.model_validate(data)

    async def send_email(self, message: TransactionalMessage) -> EmailSendResponse:
        merged = self._merge_defaults(message)
        payload = EmailSendApiRequest(message=merged).model_dump(exclude_none=True)
        url = f"{self._base_url}/email/send.json"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-KEY": self._api_key,
        }
        client = self._client()
        try:
            resp = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as e:
            raise UnisenderGoError(
                f"Unisender Go request timed out: {e}",
                status_code=None,
            ) from e
        except httpx.RequestError as e:
            raise UnisenderGoError(
                f"Unisender Go request failed: {e}",
                status_code=None,
            ) from e

        text = resp.text
        if resp.status_code >= 400:
            self._raise_from_http_error(resp.status_code, text)

        try:
            body = resp.json()
        except ValueError as e:
            raise UnisenderGoError(
                "Unisender Go returned non-JSON body",
                status_code=resp.status_code,
                response_body=text,
            ) from e

        status = body.get("status") if isinstance(body, dict) else None
        if status == "error":
            try:
                err = EmailSendErrorBody.model_validate(body)
            except ValidationError as e:
                logger.warning("Unisender Go error body parse issue: %s", text)
                raise UnisenderGoError(
                    "Unisender Go error response had unexpected shape",
                    status_code=resp.status_code,
                    response_body=text,
                ) from e
            raise UnisenderGoError(
                err.message or "Unisender Go API error",
                status_code=resp.status_code,
                api_code=err.code,
                response_body=text,
            )
        if status != "success":
            raise UnisenderGoError(
                f"Unexpected Unisender Go status: {status!r}",
                status_code=resp.status_code,
                response_body=text,
            )

        try:
            return EmailSendResponse.model_validate(body)
        except ValidationError as e:
            logger.warning("Unisender Go success response parse issue: %s", text)
            raise UnisenderGoError(
                "Unisender Go success response missing expected fields",
                status_code=resp.status_code,
                response_body=text,
            ) from e

    def _raise_from_http_error(self, status_code: int, text: str) -> None:
        try:
            raw: object = json.loads(text)
        except ValueError:
            raise UnisenderGoError(
                f"Unisender Go HTTP {status_code}",
                status_code=status_code,
                response_body=text,
            ) from None
        if isinstance(raw, dict) and raw.get("status") == "error":
            try:
                err = EmailSendErrorBody.model_validate(raw)
            except ValidationError as e:
                logger.warning("Unisender Go HTTP error body parse issue: %s", text)
                raise UnisenderGoError(
                    f"Unisender Go HTTP {status_code}",
                    status_code=status_code,
                    response_body=text,
                ) from e
            raise UnisenderGoError(
                err.message or f"Unisender Go HTTP {status_code}",
                status_code=status_code,
                api_code=err.code,
                response_body=text,
            )
        raise UnisenderGoError(
            f"Unisender Go HTTP {status_code}",
            status_code=status_code,
            response_body=text,
        )
