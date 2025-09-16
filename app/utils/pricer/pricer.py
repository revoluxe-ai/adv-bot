from sqlalchemy import func, select

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm

from ...settings import settings
from .tariffs import tariffs
from .tariffs_text import text


class Pricer:
    @property
    def text(self):
        return text

    def __init__(self):
        self._tariffs = tariffs

    @staticmethod
    async def get_advs_count(shop_id: str) -> int:
        async with sm(read_only=True) as session:
            stmt = (
                select(func.count(AdvSetting.id))
                .join(AdvSetting.wb_cabinet)
                .where(WBCabinet.shop_id == shop_id, AdvSetting.bot_active == True)
            )
            result = await session.execute(stmt)
            count_active_advs: int = result.scalar()
            return count_active_advs

    async def get_month_tariff_for_count_advs(self, shop_id: str) -> int:
        """
        Возвращает стоимость за все артикулы в зависимости от количества артикулов.
        Цена за месяц = цена_тарифа * количество_артикулов
        """
        count = await self.get_advs_count(shop_id)
        base_tariff: int = self.get_price_for_count_advs_in_cabinet_for_month(count)

        # automatic_tariff: int = await self.get_automactic_tariff(shop_id)

        return base_tariff

    @staticmethod
    def get_tariff_for_day(tariff_for_month) -> float:
        return round(tariff_for_month / 30, 2)

    async def get_price_for_day_for_shop(self, shop_id: str):
        price_for_month_for_shop = await self.get_month_tariff_for_count_advs(shop_id)
        price_for_day = self.get_tariff_for_day(price_for_month_for_shop)
        return price_for_day

    @staticmethod
    def get_price_for_count_advs_in_cabinet_for_month(count_advs: int):
        for limit, price in sorted(tariffs.items()):
            if count_advs <= limit:
                return price * count_advs
        # Если больше всех лимитов, берем максимальную цену
        return tariffs[max(tariffs)] * count_advs

    @staticmethod
    def get_payment_for_adv(sum_payment: int, count_advs: int) -> float:
        return sum_payment / count_advs

    async def get_automactic_tariff(self, shop_id: str) -> int:
        month_tariff_for_white_list_auto_updater = (
            await self._get_month_tariff_for_white_list_updater(shop_id)
        )
        month_tariff_for_autoupdate_target_place = (
            await self._get_month_tariff_for_autoupdate_target_place(shop_id)
        )
        return (
            month_tariff_for_white_list_auto_updater
            + month_tariff_for_autoupdate_target_place
        )

    async def _get_month_tariff_for_white_list_updater(self, shop_id: str) -> int:
        async with sm(read_only=True) as session:
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

    async def _get_month_tariff_for_autoupdate_target_place(self, shop_id: str) -> int:
        async with sm(read_only=True) as session:
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
