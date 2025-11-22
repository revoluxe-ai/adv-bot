from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import httpx

from app.core.mp.wb.api import AuthenticatedCastClient
from app.core.mp.wb.api.excs import (
    BadRequestError,
    UnknownApiRequestError,
    UnknownWBApiStatus,
    HttpTimeOutError,
    ApiForbiddenError,
    TooManyRequests,
)
from app.core.mp.wb.api.utils import parse_too_many_requests_error


class ResponseProtocol(Protocol):
    status_code: int
    # можно не требовать content, если он тебе не нужен в этой функции
    # content: bytes


async def with_raise_errors(
    method: Callable[..., Awaitable[Any]],
    client: AuthenticatedCastClient,
    body: Any,
) -> Any:
    try:
        result = await method(client=client, body=body)
    except httpx.TimeoutException as exc:
        raise HttpTimeOutError("Превышено время ожидания") from exc

    # здесь нам важно только то, что у result есть status_code
    status = result.status_code  # type: ignore[attr-defined]

    if 200 <= status < 300:
        return result
    elif status == 400:
        raise BadRequestError()
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
