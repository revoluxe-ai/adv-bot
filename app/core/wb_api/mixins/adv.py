import json
import logging

import aiohttp

from app.modules.common_slaves.wildberries.data_classes.adv import Adv, Balances
from .excs import (
    StartAdvError,
    ItemCategoryNotInStockError,
    AdvNotFoundInWBError,
)
from ..http_request import try_except_decorator, requests
from ..interface import InterfaceWBAPI

logger = logging.getLogger(__name__)


class AdvMixin(InterfaceWBAPI):

    @try_except_decorator(1, 2)
    async def get_advs(self, adv_ids: list[int]) -> list[Adv]:
        advs = []
        url = f"https://advert-api.wildberries.ru/adv/v1/promotion/adverts"
        async with aiohttp.ClientSession() as session:
            response_text = await requests(
                session, "POST", url, json_data=adv_ids, headers=self.headers.standart
            )
            if not response_text:
                raise AdvNotFoundInWBError(f"Не найдены РК с id {adv_ids}")

            answer = json.loads(response_text)

            adv_ids = set(adv_ids)

            for advert in answer:
                adv = Adv(advert)
                adv_id = adv.advertId
                adv_ids.discard(adv_id)
                advs.append(adv)
            if adv_ids:
                raise AdvNotFoundInWBError(f"Не найдены РК с id {adv_ids}")

        return advs

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
        self, name: str, SubjectID: int, balance_type: int, start_status
    ) -> None:
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
            if "error" in answer:
                error_text = answer["error"]
                if (
                    error_text
                    == "Invalid Params or payload: Товары выбранной категории не в наличии, размещение невозможно"
                ):
                    raise ItemCategoryNotInStockError()

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
    async def start_adv(self, adv_id: int):
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
    async def get_adv_balances(self):
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

    async def add_to_balance(self, adv_id: int, balance_type: int, sum: int):
        url = f"https://advert-api.wildberries.ru/adv/v1/budget/deposit?id={adv_id}"

        data = {"sum": sum, "type": balance_type, "return": True}

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
            for advert in adverts:
                for advert in advert["advert_list"]:
                    advertId = advert["advertId"]
                    advertIds.append(advertId)

        return advertIds

    @try_except_decorator(1, 1)
    async def update_cpm(self, adv_id, new_cpm):
        url = "https://advert-api.wildberries.ru/adv/v0/cpm"
        data = {
            "advertId": adv_id,
            "type": 8,
            "cpm": int(new_cpm),
            # "param": None
        }
        async with aiohttp.ClientSession() as session:
            response_text = await requests(
                session, "POST", url, json_data=data, headers=self.headers.standart
            )

            assert response_text == ""
            pass

    @try_except_decorator(1, 1)
    async def set_search_cpm(self, search_adv_id: int, cpm: int):
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
