"""
Протокол для работы с  WB API

"""

from typing import Protocol, runtime_checkable

from app.modules.common_slaves.wildberries.ABC_WB_API import Headers


@runtime_checkable
class WBAPIProtocol(Protocol):
    """
    Протокол для работы с WB API.
    """

    async def set_next_token(self) -> None:
        """
        Устанавливает следующий токен для доступа к API.
        """
        pass

    @property
    def headers(self) -> Headers:
        """
        Возвращает заголовки для доступа к API.
        """
        pass

    @property
    def shop_id(self) -> str:
        """
        Возвращает идентификатор магазина.
        """
        pass

    @property
    def api_call_state(self) -> dict[str, dict]:
        """
        Возвращает состояние вызова API.
        """
        pass

    @api_call_state.setter
    def api_call_state(self, value: dict[str, dict]) -> None:
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
