"""
Протокол для работы с  WB API

"""

from typing import Protocol, runtime_checkable, Any

from ...modules.common_slaves.wildberries.ABC_WB_API import Headers


@runtime_checkable
class WBAPIProtocol(Protocol):
    """Протокол для работы с WB API для миксинов"""

    headers: Headers
    HOST: str
    api_call_state: dict[str, dict[str, Any]]
    shop_id: str

    async def set_next_token(self) -> None:
        """Устанавливает следующий токен для работы с API"""

    ...
