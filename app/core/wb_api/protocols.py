"""
Протокол для работы с  WB API

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from aiohttp import ClientSession

if TYPE_CHECKING:
    from ...modules.common_slaves.wildberries.ABC_WB_API import Headers


@runtime_checkable
class WBAPIProtocol(Protocol):
    """Протокол для работы с WB API для миксинов"""

    PREFIX: str
    headers: "Headers"
    HOST: str
    api_call_state: dict[str, dict[str, Any]]
    shop_id: str
    session: ClientSession

    async def set_next_token(self, method_name: str) -> None:
        """Устанавливает следующий токен для работы с API"""

    ...
