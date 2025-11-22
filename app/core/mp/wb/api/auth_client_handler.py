from collections.abc import Callable

import httpx
from hashlib import sha256

import typing

from app.core.mp.wb.api.excs import ApiForbiddenError
from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler

if typing.TYPE_CHECKING:
    from app.core.mp.wb.api.adapter.abc_group_client import AbcAdapter
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.models import WBToken
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.core.mp.wb.api.adapter.sections_enum import SectionsEnum
from app.core.mp.wb.api.api_client import AuthenticatedCastClient




class AuthClientHandler:
    def __init__(self, shop_id: str, httpx_client_handler: HttpxClientHandler) -> None:
        self.__httpx_client_handler = httpx_client_handler
        self.__shop_id: str = shop_id
        self._access: WBCabinetAccess | None = None
        self._httpx_clients: dict[SectionsEnum, httpx.AsyncClient] = {}
        self._not_working_tokens_hash: set[str] = set()

    @property
    def shop_id(self) -> str:
        return self.__shop_id


    async def get_proxy_client(self, adapter: 'AbcAdapter', ) -> AuthenticatedCastClient:
        section = adapter.section
        token = await self.__get_actual_token(section)
        if token is None:
            raise ApiForbiddenError('Нет доступных токенов')

        httpx_client: httpx.AsyncClient = self.__httpx_client_handler.get_httpx_client(section)
        client = AuthenticatedCastClient(adapter.base_url,
                                         httpx_client,
                                         token,
                                         raise_on_unexpected_status=False)
        return client


    async def __get_actual_token(self, section: SectionsEnum) -> str | None:
        if self._access is None:
            await self._update_access()
        access: WBCabinetAccess | None = self._access
        assert access is not None
        tokens = access.tokens
        filter_func = self.__get_token_filter_func(section)
        filtred_tokens: list[WBToken] = list(filter(filter_func, tokens))

        if not filtred_tokens:
            return None
        else:
            return filtred_tokens[0].api_key



    def __get_token_filter_func(self, section: SectionsEnum) -> Callable[[WBToken], bool]:
        sections_map = {
            SectionsEnum.PROMOTION: "Продвижение",
            SectionsEnum.ANALYTIC_AND_DATA: 'Аналитика'

        }

        def func(token: WBToken):
            token_hash = self._get_token_hash(token)
            if token_hash in self._not_working_tokens_hash:
                return False
            ru_section_name = sections_map[section]
            if token.is_expired:
                return False
            if ru_section_name in token.categories:
                return True
            return False
        return func

    async def _update_access(self) -> None:
        self._access = await super_cabinet_manager.get_access_for_wb_cabinet(self.__shop_id)
        return None

    @staticmethod
    def _get_token_hash(token: WBToken) -> str:
        token_str = token.api_key
        return str(sha256(token_str.encode("utf-8")))




















