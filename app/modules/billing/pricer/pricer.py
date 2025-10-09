"""Модуль для расчета стоимости тарифов."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.settings import settings
from app.utils.db.session_maker import get_async_session_maker as sm
from .tariffs import tariffs
from .tariffs_text import text


class Pricer:
    """Класс для расчета стоимости тарифов."""

    @property
    def text(self):
        return text

    def __init__(self) -> None:
        self._tariffs = tariffs

    @staticmethod
    async def get_advs_count(session: AsyncSession, shop_id: str) -> int:
        stmt = (
            select(func.count(AdvSetting.id))
            .join(AdvSetting.wb_cabinet)
            .where(WBCabinet.shop_id == shop_id, AdvSetting.bot_active == True)
        )
        result = await session.execute(stmt)
        count_active_advs: int | None = result.scalar()
        count_active_advs = count_active_advs or 0
        return count_active_advs

    async def get_month_tariff_for_count_advs(self, session: AsyncSession, shop_id: str) -> int:
        """
        Возвращает стоимость за все артикулы в зависимости от количества артикулов.
        Цена за месяц = цена_тарифа * количество_артикулов
        """
        count = await self.get_advs_count(session, shop_id)
        base_tariff: int | float = self.get_price_for_count_advs_in_cabinet_for_month(count)
        automatic_tariff: int = await self.get_automactic_tariff(session, shop_id)
        return int(base_tariff + automatic_tariff)



    @staticmethod
    def get_tariff_for_day(tariff_for_month: int) -> float:
        return round(tariff_for_month / 30, 2)

    async def get_price_for_day_for_shop(self, session: AsyncSession, shop_id: str) -> int | float:
        price_for_month_for_shop = await self.get_month_tariff_for_count_advs(session, shop_id)
        price_for_day = self.get_tariff_for_day(price_for_month_for_shop)
        return price_for_day

    @staticmethod
    def get_price_for_count_advs_in_cabinet_for_month(count_advs: int) -> float:
        for limit, price in sorted(tariffs.items()):
            if count_advs <= limit:
                return price * count_advs
        # Если больше всех лимитов, берем максимальную цену
        return tariffs[max(tariffs)] * count_advs

    @staticmethod
    def get_payment_for_adv(sum_payment: int, count_advs: int) -> float:
        return sum_payment / count_advs

    async def get_automactic_tariff(self, session: AsyncSession, shop_id: str) -> int:
        month_tariff_for_white_list_auto_updater = await self._get_month_tariff_for_white_list_updater(session,
                                                                                                       shop_id)
        month_tariff_for_autoupdate_target_place = await self._get_month_tariff_for_autoupdate_target_place(session,
                                                                                                            shop_id)
        return month_tariff_for_white_list_auto_updater + month_tariff_for_autoupdate_target_place

    @staticmethod
    async def _get_month_tariff_for_white_list_updater(session: AsyncSession, shop_id: str) -> int:
        stmt = (
            select(func.count(AdvSetting.id))
            .join(WBCabinet)
            .where(
                WBCabinet.shop_id == shop_id,
                AdvSetting.auto_update_white_list == True,
            )
        )
        result = await session.execute(stmt)
        count = result.scalar() or 0
        count = int(count)
        sum_result: int = count * settings.WHITE_LIST_AUTO_UPDATER_MONTH_TARIFF
        return sum_result

    @staticmethod
    async def _get_month_tariff_for_autoupdate_target_place(session: AsyncSession, shop_id: str) -> int:
        stmt = (
            select(func.count(AdvSetting.id))
            .join(WBCabinet)
            .where(
                WBCabinet.shop_id == shop_id,
                AdvSetting.auto_update_target_place == True,
            )
        )
        result = await session.execute(stmt)
        count = result.scalar() or 0
        count = int(count)
        return count * settings.AUTO_UPDATE_TARGET_PLACE_MONTH_TARIFF
