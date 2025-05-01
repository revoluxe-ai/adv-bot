"""
Протокол для работы с  WB API

"""

from typing import Protocol, runtime_checkable, Any

from ...modules.common_slaves.wildberries.ABC_WB_API import Headers


@runtime_checkable
class WBAPIProtocol(Protocol):

    headers: Headers
    """
    Протокол для работы с WB API.
    """

    async def set_next_token(self) -> None:
        """
        Устанавливает следующий токен для доступа к API.
        """
        pass

    @property
    def shop_id(self) -> str:
        """
        Возвращает идентификатор магазина.
        """
        pass

    @property
    def api_call_state(self) -> dict[str, dict[str, Any]]:
        """
        Возвращает состояние вызова API.
        """
        pass

    @api_call_state.setter
    def api_call_state(self, value: dict[str, dict[str, Any]]) -> None:
        """
        Устанавливает состояние вызова API.
        """
        pass

    @property
    def HOST(self) -> str:
        """
        Возвращает хост для доступа к API.
        """
        pass
