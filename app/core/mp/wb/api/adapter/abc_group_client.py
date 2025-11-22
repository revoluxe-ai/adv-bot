from abc import ABC

from .sections_enum import SectionsEnum
from ..auth_client_handler import AuthClientHandler
from ..request_limit_manager import ApiCallState, RequestLimitManager


class AbcAdapter(ABC):
    section: SectionsEnum

    def __init__(
        self,
        base_url: str,
        auth_client_handler: "AuthClientHandler",
        request_limit_manager: RequestLimitManager,
    ) -> None:
        self.__base_url = base_url
        self.__auth_client_handler = auth_client_handler
        self.__request_limit_manager = request_limit_manager
        self.__shop_id = self.__auth_client_handler.shop_id
        self.api_call_state: dict[str, ApiCallState] = (
            self.__request_limit_manager.api_call_state
        )

    @property
    def auth_client_handler(self) -> "AuthClientHandler":
        return self.__auth_client_handler

    @property
    def request_limit_manager(self) -> RequestLimitManager:
        return self.__request_limit_manager

    @property
    def base_url(self) -> str:
        return self.__base_url

    @property
    def shop_id(self) -> str:
        return self.__shop_id
