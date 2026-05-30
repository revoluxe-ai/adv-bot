"""Преобразование httpx-ответов и сетевых ошибок WB API в доменные исключения."""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol
import logging

import httpcore
import httpx

from app.core.mp.wb.api import AuthenticatedCastClient
from app.core.mp.wb.api.excs import (
    BadRequestError,
    UnknownApiRequestError,
    UnknownWBApiStatus,
    HttpTimeOutError,
    PoolTimeoutError,
    ApiForbiddenError,
    TooManyRequests,
)

from app.core.mp.wb.api.utils import parse_too_many_requests_error


logger = logging.getLogger(__name__)


class ResponseProtocol(Protocol):
    status_code: int
    # можно не требовать content, если он тебе не нужен в этой функции
    # content: bytes


def _timeout_exc_type(exc: Exception) -> str:
    return type(exc).__name__


def _extract_items_count(kwargs: dict[str, Any]) -> int | None:
    """Оценка размера batch-запроса из kwargs generated-клиента, если доступно."""
    body = kwargs.get("body")
    if body is not None:
        items = getattr(body, "items", None)
        if items is not None:
            return len(items)
    ids = kwargs.get("ids")
    if isinstance(ids, str) and ids:
        return len(ids.split(","))
    return None


def _log_http_timeout(
    *,
    exc: Exception,
    endpoint: str,
    section_name: str,
    items_count: int | None,
) -> None:
    exc_type = _timeout_exc_type(exc)
    if isinstance(exc, (httpcore.PoolTimeout, httpx.PoolTimeout)):
        logger.warning(
            "WB HTTP pool timeout: exc_type=PoolTimeout endpoint=%s section=%s items_count=%s",
            endpoint,
            section_name,
            items_count,
        )
    else:
        logger.warning(
            "WB HTTP timeout: exc_type=%s endpoint=%s section=%s items_count=%s",
            exc_type,
            endpoint,
            section_name,
            items_count,
        )


async def with_raise_errors(
    method: Callable[..., Awaitable[Any]],
    client: AuthenticatedCastClient,
    **kwargs: Any,
) -> Any:
    endpoint = getattr(method, "__name__", "unknown")
    section_name = client.section.name if client.section is not None else "unknown"
    items_count = _extract_items_count(kwargs)

    try:
        result = await method(client=client, **kwargs)
    except (httpx.TimeoutException, httpcore.PoolTimeout) as exc:
        _log_http_timeout(
            exc=exc,
            endpoint=endpoint,
            section_name=section_name,
            items_count=items_count,
        )
        if isinstance(exc, (httpcore.PoolTimeout, httpx.PoolTimeout)):
            raise PoolTimeoutError(original_exc=exc) from exc
        exc_type = _timeout_exc_type(exc)
        raise HttpTimeOutError(
            f"Превышено время ожидания (exc_type={exc_type})"
        ) from exc

    # здесь нам важно только то, что у result есть status_code
    status = result.status_code

    if 200 <= status < 300:
        return result
    elif status in [400, 404, 422]:
        # 422: в т.ч. «AdvertChangeStatus: Low Budget» на /adv/v0/start (см. get_adv_v0_start)
        detail = result.content.decode()
        raise BadRequestError(detail)
    elif status in [401, 403]:
        raise ApiForbiddenError(
            text="Неверный токен",
            not_valid_token_hash=client.token_hash,
            section=client.section,
        )
    elif status == 429:
        next_pause: int | None = parse_too_many_requests_error(result)
        raise TooManyRequests(next_pause=next_pause)
    elif status >= 500:
        raise UnknownApiRequestError()
    else:
        raise UnknownWBApiStatus("Не известный статус ответа")
