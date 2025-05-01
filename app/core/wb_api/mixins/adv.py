import json
import logging
from typing import Any
from typing import TypeVar

import aiohttp

from app.core.wb_api.data_classes.adv import Adv
from app.core.wb_api.protocols import WBAPIProtocol
from app.modules.common_slaves.wildberries.data_classes.adv import Balances
from .excs import (
    StartAdvError,
    ItemCategoryNotInStockError,
)
from ..data_classes.advs import adv_fabric
from ..http_request import try_except_decorator, requests

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=WBAPIProtocol)


class MinCPMData:
    def __init__(self, api_answer: dict[str, Any]):
        category_id_to_min_cpm: dict[int, int] = {}
        category_name_to_min_cpm: dict[str, int] = {}

        for data in api_answer["categories"]:
            category_id = data["id"]
            category_name = data["name"]
            min_cpm = data["cpm_min"]
            category_id_to_min_cpm[category_id] = min_cpm
            category_name_to_min_cpm[category_name] = min_cpm

        self.category_id_to_min_cpm = category_id_to_min_cpm
        self.category_name_to_min_cpm = category_name_to_min_cpm

    def get_min_cpm_data_for_cagegory_name_match(self) -> dict[str, int]:
        return self.category_name_to_min_cpm


class AdvMixin(WBAPIProtocol):

    PREFIX = "https://advert-api"

    @try_except_decorator(1, 60)
    async def get_min_cpm_adv_data(self) -> MinCPMData:
        url = f"{self.PREFIX}.{self.HOST}/adv/v0/config"
        async with aiohttp.ClientSession() as session:
            response_text = await requests(
                session, "GET", url, headers=self.headers.standart
            )
            answer = json.loads(response_text)
            return MinCPMData(answer)

    @try_except_decorator(1, 3)
    async def get_advertIds(self: T) -> list[int]:
        advertIds: list[int] = []
        url = "https://advert-api.wildberries.ru/adv/v1/promotion/count"

        async with aiohttp.ClientSession() as session:
            response_text: str = await requests(
                session, "GET", url, headers=self.headers.standart
            )
            answer: dict[str, Any] = json.loads(response_text)

            adverts: list[dict[str, Any]] = answer.get("adverts", [])

            if not adverts:
                return []

            for advert in adverts:
                advert_type = advert.get("type")
                if isinstance(advert_type, int) and advert_type == 8:
                    advert_list: list[dict[str, Any]] = advert.get("advert_list", [])
                    for advert_item in advert_list:
                        advertId = advert_item["advertId"]
                        advertIds.append(advertId)

        return advertIds

    @try_except_decorator(1, 2)
    async def _get_advs(self, adv_ids: list[int]) -> list[Adv]:
        advs = []
        url = f"https://advert-api.wildberries.ru/adv/v1/promotion/adverts"
        async with aiohttp.ClientSession() as session:
            response_text = await requests(
                session, "POST", url, json_data=adv_ids, headers=self.headers.standart
            )
            answer = json.loads(response_text)
            for advert in answer:
                adv: Adv | None = adv_fabric.get_adv_data_class(advert)
                if adv:
                    advs.append(adv)
        return advs

    @try_except_decorator(1, 1)
    async def get_advs(self, adv_ids: list[int] | None = None) -> list[Adv]:
        if not adv_ids:
            adv_ids: list[int] = await self.get_advertIds()
        all_advs = []
        part = 50
        for i in range(0, len(adv_ids), part):
            part_of_advs = adv_ids[i : i + part]
            advs = await self._get_advs(part_of_advs)
            all_advs.extend(advs)
        return all_advs

    @try_except_decorator(5, 60)
    async def create_search_adv(self, nmids: list[int], adv_name: str) -> int:
        assert len(nmids) <= 50

        url = f"https://advert-api.wildberries.ru/adv/v2/seacat/save-ad"

        data = {"campaignName": adv_name, "nms": nmids}

        async with aiohttp.ClientSession() as session:
            response_text = await requests(
                session, "POST", url, json_data=data, headers=self.headers.standart
            )
            answer = json.loads(response_text)
            return answer

    @try_except_decorator(1, 60)
    async def create_auto_adv(
        self, name: str, SubjectID: int, balance_type: int, start_status: bool
    ) -> int | None:
        url = f"https://advert-api.wildberries.ru/adv/v1/save-ad"
        data = {
            "type": 8,
            "name": name[:128],
            "subjectId": SubjectID,
            "sum": 1000,
            "btype": balance_type,
            "on_pause": False if start_status else True,
        }

        async with aiohttp.ClientSession() as session:
            response_text = await requests(
                session, "POST", url, json_data=data, headers=self.headers.standart
            )
            answer = json.loads(response_text)
            if isinstance(answer, int):
                return answer
            elif "error" in answer:
                error_text = answer["error"]
                if (
                    error_text == "Invalid Params or payload:"
                    " Товары выбранной категории не в наличии, размещение невозможно"
                ):
                    raise ItemCategoryNotInStockError()
            else:
                raise Exception("Неизвестная ошибка создания РК")

    @try_except_decorator(1, 20)
    async def check_balance(self, adv_id: int):
        url = f"https://advert-api.wildberries.ru/adv/v0/get-balance/{adv_id}"
        async with aiohttp.ClientSession() as session:
            response_text = await requests(
                session, "GET", url, headers=self.headers.standart
            )
            answer = json.loads(response_text)
            return answer

    @try_except_decorator(1, 10)
    async def start_adv(self, adv_id: int) -> None:
        try:
            url = f"https://advert-api.wildberries.ru/adv/v0/start?id={adv_id}"
            async with aiohttp.ClientSession() as session:
                response = await requests(
                    session, "GET", url, headers=self.headers.standart
                )
                if response != "":
                    raise StartAdvError()
        except Exception as exc:
            raise StartAdvError(
                f"Не удалось запустить компанию {adv_id}. Ошибка: {exc}"
            )

    @try_except_decorator(1, 10)
    async def get_adv_balances(self) -> Balances:
        url = "https://advert-api.wildberries.ru/adv/v1/balance"
        async with aiohttp.ClientSession() as session:
            response = await requests(
                session, "GET", url=url, headers=self.headers.standart
            )
            response = json.loads(response)
            logger.debug(f"Ответ на получение баланса: {response}")
            balance = Balances(response)
            return balance

    @try_except_decorator(1, 1)
    async def rename_adv(self, adv_id: int, new_name: str) -> None:
        url = "https://advert-api.wildberries.ru/adv/v0/rename"

        data = {"advertId": adv_id, "name": new_name}

        async with aiohttp.ClientSession() as session:
            await requests(
                session, "POST", url, json_data=data, headers=self.headers.standart
            )
            return None

    async def update_nmids_in_adv(
        self, adv_id: int, nmids_for_add: list[int], nmids_for_del: list[int]
    ):
        url = f"https://advert-api.wildberries.ru/adv/v1/auto/updatenm?id={adv_id}"
        data = {"add": nmids_for_add, "delete": nmids_for_del}

        async with aiohttp.ClientSession() as session:
            await requests(
                session, "POST", url, json_data=data, headers=self.headers.standart
            )

    @try_except_decorator(1, 2)
    async def get_nmids_to_add(self, adv_id: int) -> list[int]:
        url = f"https://advert-api.wildberries.ru/adv/v1/auto/getnmtoadd?id={adv_id}"
        async with aiohttp.ClientSession() as session:
            response_text = await requests(
                session, "GET", url, headers=self.headers.standart
            )
            answer = json.loads(response_text)
            if answer is None:
                return []
            return answer

    @try_except_decorator(1, 2)
    async def update_nmids_in_auto_adv(
        self, adv_id: int, nmids_for_add: list[int], nmids_for_del: list[int]
    ):
        url = f"https://advert-api.wildberries.ru/adv/v1/auto/updatenm?id={adv_id}"
        data = {"add": nmids_for_add, "delete": nmids_for_del}

        async with aiohttp.ClientSession() as session:
            await requests(
                session, "POST", url, json_data=data, headers=self.headers.standart
            )

    async def add_to_balance(self, adv_id: int, balance_type: int, sum_: int):
        url = f"https://advert-api.wildberries.ru/adv/v1/budget/deposit?id={adv_id}"

        data = {"sum": sum_, "type": balance_type, "return": True}

        async with aiohttp.ClientSession() as session:
            response_text = await requests(
                session, "POST", url, json_data=data, headers=self.headers.standart
            )
            answer = json.loads(response_text)
            new_balance = answer["total"]
            return new_balance

    async def stop_adv(self, adv_id: int):
        url = f"https://advert-api.wildberries.ru/adv/v0/pause?id={adv_id}"
        async with aiohttp.ClientSession() as session:
            await requests(session, "GET", url, headers=self.headers.standart)
            return None

    @try_except_decorator(1, 3)
    async def get_all_adv_ids(self) -> list[int]:
        advertIds = []
        url = "https://advert-api.wildberries.ru/adv/v1/promotion/count"
        async with aiohttp.ClientSession() as session:
            response_text = await requests(
                session, "GET", url, headers=self.headers.standart
            )
            answer = json.loads(response_text)
            # Используем json.loads для преобразования текста ответа в JSON
            adverts: list = answer["adverts"]
            if not adverts:
                return []
            for advert_data in adverts:
                for advert in advert_data["advert_list"]:
                    advertId = advert["advertId"]
                    advertIds.append(advertId)

        return advertIds

    @try_except_decorator(5, 60)
    async def update_cpm(self, adv_id: int, nmid: int, new_bid: int) -> None:
        url = "https://advert-api.wildberries.ru/adv/v0/bids"
        data = {
            "bids": [{"advert_id": adv_id, "nm_bids": [{"nm": nmid, "bid": new_bid}]}]
        }
        async with aiohttp.ClientSession() as session:
            await requests(
                session, "PATCH", url, json_data=data, headers=self.headers.standart
            )

    @try_except_decorator(1, 1)
    async def set_search_cpm(self, search_adv_id: int, cpm: int) -> None:
        url = "https://advert-api.wildberries.ru/adv/v0/cpm"
        data = {"advertId": search_adv_id, "type": 9, "cpm": cpm}
        async with aiohttp.ClientSession() as session:
            response = await requests(
                session, "POST", url, json_data=data, headers=self.headers.standart
            )
            if response == "":
                logger.debug(f"CPM для поисковой кампании {search_adv_id} установлен")
                return
            else:
                logger.error(
                    f"Ошибка установки CPM для поисковой кампании {search_adv_id}, ответ: {response}"
                )
