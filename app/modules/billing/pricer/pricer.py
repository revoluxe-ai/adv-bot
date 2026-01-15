"""Модуль для расчета стоимости тарифов."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum, auto

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from .tariffs import tariffs, tariffs_for_auto_setting
from .tariffs_text import text


class TariffMode(StrEnum):
    OLD = auto()
    AUTO = auto()


@dataclass(slots=True)
class TariffDetails:
    mode: TariffMode
    count: int
    price_per_adv: float
    total_per_month: float
    total_per_day: float


@dataclass(slots=True)
class TariffContext:
    count: int
    has_auto: bool


class Pricer:
    """Класс для расчета стоимости тарифов."""

    @property
    def text(self):
        return text

    def __init__(self) -> None:
        self._tariffs = tariffs

    @staticmethod
    async def get_active_complex_advs_count(
        session: AsyncSession, shop_id: str
    ) -> int:
        context = await Pricer.calculate_tariff_context(session, shop_id)
        return context.count

    async def get_month_tariff_for_count_advs(
        self, session: AsyncSession, shop_id: str
    ) -> int:
        """
        Возвращает стоимость за все артикулы в зависимости от количества артикулов.
        Цена за месяц = цена_тарифа * количество_артикулов
        """
        details = await self.get_tariff_details(session, shop_id)
        return int(details.total_per_month)

    @staticmethod
    def get_tariff_for_day(tariff_for_month: float) -> float:
        return round(tariff_for_month / 30, 2)

    async def get_price_for_day_for_shop(
        self, session: AsyncSession, shop_id: str
    ) -> float:
        details = await self.get_tariff_details(session, shop_id)
        return details.total_per_day

    def get_price_for_count_advs_in_cabinet_for_month(
        self, count_advs: int, tariff_table: dict[int, int] | None = None
    ) -> float:
        table = tariff_table or self._tariffs
        price_per_adv = self._get_price_per_adv(count_advs, table)
        return price_per_adv * count_advs

    @staticmethod
    def get_payment_for_adv(sum_payment: int, count_advs: int) -> float:
        return sum_payment / count_advs

    async def get_tariff_details(
        self, session: AsyncSession, shop_id: str
    ) -> TariffDetails:
        context = await self.calculate_tariff_context(session, shop_id)
        mode = TariffMode.AUTO if context.has_auto else TariffMode.OLD
        tariff_table = tariffs_for_auto_setting if mode == TariffMode.AUTO else self._tariffs
        price_per_adv = self._get_price_per_adv(context.count, tariff_table)
        total_per_month = price_per_adv * context.count
        total_per_day = self.get_tariff_for_day(total_per_month) if total_per_month else 0.0
        return TariffDetails(
            mode=mode,
            count=context.count,
            price_per_adv=price_per_adv,
            total_per_month=total_per_month,
            total_per_day=total_per_day,
        )

    @staticmethod
    async def calculate_tariff_context(
        session: AsyncSession, shop_id: str
    ) -> TariffContext:
        auto_advs = await Pricer.fetch_bot_active_advs(session, shop_id)
        if not auto_advs:
            return TariffContext(count=0, has_auto=False)

        has_auto = any(Pricer.is_part_auto_setting_active(adv) for adv in auto_advs)
        active_auto_advs = await Pricer.fetch_tariff_auto_advs(
            session, shop_id, auto_advs=auto_advs
        )

        return TariffContext(count=len(active_auto_advs), has_auto=has_auto)

    @staticmethod
    async def fetch_bot_active_advs(
        session: AsyncSession, shop_id: str
    ) -> Sequence[AdvSetting]:
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .where(
                WBCabinet.shop_id == shop_id,
                AdvSetting.bot_active.is_(True),
            )
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def fetch_active_search_adv_ids(
        session: AsyncSession, search_adv_ids: Sequence[int]
    ) -> set[int]:
        if not search_adv_ids:
            return set()
        stmt = select(AdvSetting.adv_id).where(
            AdvSetting.adv_id.in_(search_adv_ids),
            AdvSetting.active_status == "started",
        )
        result = await session.execute(stmt)
        return set(result.scalars().all())

    @staticmethod
    async def _fetch_active_search_adv_ids(
        session: AsyncSession, search_adv_ids: Sequence[int]
    ) -> set[int]:
        """Backwards-compatible alias (старое имя метода)."""
        return await Pricer.fetch_active_search_adv_ids(session, search_adv_ids)

    @staticmethod
    async def fetch_tariff_auto_advs(
        session: AsyncSession,
        shop_id: str,
        *,
        auto_advs: Sequence[AdvSetting] | None = None,
    ) -> Sequence[AdvSetting]:
        """Возвращает auto-кампании, которые участвуют в тарификации.

        Правило на текущий момент:
        - AdvSetting.bot_active == True
        - search-кампания (search_adv_id) имеет active_status == 'started'
        """
        if auto_advs is None:
            auto_advs = await Pricer.fetch_bot_active_advs(session, shop_id)
        if not auto_advs:
            return []

        search_adv_ids = [adv.search_adv_id for adv in auto_advs if adv.search_adv_id]
        if not search_adv_ids:
            return []

        active_search_adv_ids = await Pricer.fetch_active_search_adv_ids(
            session, search_adv_ids
        )
        if not active_search_adv_ids:
            return []

        return [adv for adv in auto_advs if adv.search_adv_id in active_search_adv_ids]

    @staticmethod
    def is_part_auto_setting_active(adv: AdvSetting) -> bool:
        auto_version = adv.automatic_version or 0
        white_list_active = bool(adv.auto_update_white_list)
        target_place_active = bool(adv.auto_update_target_place)
        if auto_version == 1:
            return white_list_active or target_place_active
        if auto_version == 2:
            return white_list_active or target_place_active
        return False

    @staticmethod
    def _get_price_per_adv(count_advs: int, tariff_table: dict[int, int]) -> float:
        if count_advs <= 0:
            return 0.0
        for limit in sorted(tariff_table):
            if count_advs <= limit:
                return float(tariff_table[limit])
        max_limit = max(tariff_table)
        return float(tariff_table[max_limit])


# TODO: Сделать уведомлялку по API
# TODO: Сделать сайт с отзывами
# TODO: Сделать инструкцию по скриншотам через Яндекс.Диск
