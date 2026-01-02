from datetime import datetime
from app.core.di.wb_manager_hub import WBManagerHub
from app.core.mp.wb.dto import KeywordPosition
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
from .click_house_manager import ClickHouseKeywordJamStatManager
from .keyword_stamp import KeywordStamp
from zoneinfo import ZoneInfo
from typing import Sequence
import logging


# TODO: Исправить создание РК для нового бота


logger = logging.getLogger(__name__)


class KeywordStampManager:

    def __init__(
        self,
        wb_api_manager_hub: WBManagerHub,
        click_house_manager: ClickHouseKeywordJamStatManager,
    ):
        self._click_house = click_house_manager
        self._wb_api = wb_api_manager_hub

    async def update_keyword_history(self, adv: ComplexAdv) -> None:
        try:
            await self._update_keyword_history(adv)
        except Exception as e:
            logger.error("Ошибка обновления истории ключей: %s", e, exc_info=True)
            raise e

    async def _update_keyword_history(self, complex_adv: ComplexAdv) -> None:
        keywords = await complex_adv.get_keywords()
        keywords_with_views: list[CalculatedKeyword] = [
            kw for kw in keywords if kw.views > 0
        ]
        nmid: int = complex_adv.main_nmid
        positions: Sequence[KeywordPosition] = (
            await self._wb_api.wb_data_manager.get_keywords_positions_from_wb_api(
                nmid, keywords_with_views, for_last_days=7
            )
        )

        try:
            await self._click_house.update_positions(positions)
        except Exception:
            logger.error(
                "Ошибка обновления позиций в CH, shop_id: %s, adv_id: %s",
                complex_adv.shop_id,
                complex_adv.adv_id,
                exc_info=True,
            )
            raise
        return None

    async def update_keywords_position_stamp(self, complex_adv: ComplexAdv) -> None:
        try:
            await self._update_keywords_position_stamp(complex_adv)
        except Exception as e:
            logger.error("Ошибка обновления stamps ключей %s", e, exc_info=True)
            raise e

    async def _update_keywords_position_stamp(self, complex_adv: ComplexAdv) -> None:
        keywords = await complex_adv.get_keywords()
        keywords_with_views: list[CalculatedKeyword] = [
            kw for kw in keywords if kw.views > 0
        ]
        nmid: int = complex_adv.main_nmid
        positions: Sequence[KeywordPosition] = (
            await self._wb_api.wb_data_manager.get_keywords_positions_from_wb_api(
                nmid, keywords_with_views, for_last_days=1
            )
        )

        # TODO: Реализовать отметку в кабинете о ApiForbiddenError

        keywords_map = {kw.text: kw for kw in keywords_with_views}
        current_cpm = self._get_current_cpm(complex_adv)
        stamps: list[KeywordStamp] = []
        for position in positions:
            keyword_cmp = self.__get_keyword_cpm(
                keywords_map[position.text], current_cpm
            )
            kw_stamp = KeywordStamp(
                shop_id=complex_adv.shop_id,
                nmid=nmid,
                adv_id=complex_adv.adv_id,
                text=position.text,
                avr_position=position.average_position,
                orders=position.orders,
                total_views=position.total_views_avr_for_day,
                date=position.date,
                current_cpm=keyword_cmp,
                timestamp=datetime.now(ZoneInfo("Europe/Moscow")),
            )
            stamps.append(kw_stamp)

        try:
            await self._update_kw_stamp_in_clickhouse(stamps)
        except Exception:
            logger.error(
                "Ошибка обновления stamps, shop_id: %s, adv_id: %s, stamps: %s",
                complex_adv.shop_id,
                complex_adv.adv_id,
                stamps,
                exc_info=True,
            )
            raise
        # TODO: Сделать обновление сервисом по коммитам
        return None

    @staticmethod
    def _get_current_cpm(complex_adv: ComplexAdv) -> int:
        cpms: list[int] = []
        if complex_adv.adv_setting.active_status == "started":
            cpms.append(complex_adv.current_cpms.auto_cpm)
        if search_adv := complex_adv.search_adv:
            if search_adv.active_status == "started":
                search_cpm = complex_adv.current_cpms.search_cpm
                if search_cpm is not None:
                    cpms.append(search_cpm)
        if not cpms:
            return 0
        else:
            return max(cpms)

    async def _update_kw_stamp_in_clickhouse(self, stamps: list[KeywordStamp]) -> None:
        await self._click_house.update_stamps(stamps)
        return None

    @staticmethod
    def __get_keyword_cpm(keyword: CalculatedKeyword, current_cpm: int):
        return current_cpm if keyword.status == KeywordStatus.GOOD else 0
