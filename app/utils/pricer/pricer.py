from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm
from sqlalchemy import select, func
from .tariffs import tariffs
from .tariffs_text import text

class Pricer:

    @property
    def text(self):
        return text

    def __init__(self):
        self._tariffs = tariffs


    async def get_advs_count(self, shop_id: str) -> int:
        async with sm(read_only=True) as session:
            stmt = select(func.count(AdvSetting.id))\
            .join(AdvSetting.wb_cabinet)\
                .where(WBCabinet.shop_id == shop_id,
                       AdvSetting.bot_active == True)
            result = await session.execute(stmt)
            count_active_advs = result.scalar()
            return count_active_advs


    async def get_month_tariff_for_count_advs(self, shop_id: str) -> int:
        """
            Возвращает стоимость за все артикулы в зависимости от количества артикулов.
            Цена за месяц = цена_тарифа * количество_артикулов
        """
        count = await self.get_advs_count(shop_id)

        for limit, price in sorted(tariffs.items()):
            if count <= limit:
                return price * count
        # Если больше всех лимитов, берем максимальную цену
        return tariffs[max(tariffs)] * count

    @staticmethod
    def get_tariff_for_day(tariff_for_month) -> float:
        return round(tariff_for_month/30, 2)

    async def get_price_for_day_for_shop(self, shop_id: str):
        price_for_month_for_shop = await self.get_month_tariff_for_count_advs(shop_id)
        price_for_day = self.get_tariff_for_day(price_for_month_for_shop)
        return price_for_day













