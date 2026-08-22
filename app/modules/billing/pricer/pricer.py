"""Модуль для расчета стоимости тарифов."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum, auto

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.leg_latch import LegLatchManager
from app.modules.billing.tariff_preview_context import (
    resolve_tariff_preview_latch_context,
)
from app.modules.billing.leg_metering import (
    compute_cabinet_billable_units,
    fetch_cabinet_adv_settings_for_metering,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from .tariffs import tariffs, tariffs_for_auto_setting
from .tariffs_text import text
from ...common_slaves.wildberries.models.wb_cabinet import WBCabinet


class TariffMode(StrEnum):
    OLD = auto()
    AUTO = auto()


@dataclass(slots=True)
class TariffDetails:
    mode: TariffMode
    count: float
    price_per_adv: float
    total_per_month: float
    total_per_day: float


@dataclass(slots=True)
class TariffContext:
    count: float
    has_auto: bool


class Pricer:
    """Класс для расчета стоимости тарифов."""

    @property
    def text(self):
        return text

    def __init__(self) -> None:
        self._tariffs = tariffs
        self._last_explicit_preview_latch: LegLatchManager | None = None
        self._last_explicit_preview_utc_date: date | None = None

    @staticmethod
    async def get_active_complex_advs_count(
        session: AsyncSession, shop_id: str
    ) -> int:
        context = await Pricer.calculate_tariff_context(session, shop_id)
        return int(round(context.count))

    async def get_month_tariff_for_count_advs(
        self, session: AsyncSession, shop_id: str
    ) -> int:
        """
        Возвращает стоимость за все артикулы в зависимости от количества артикулов.
        Цена за месяц = цена_тарифа * количество_артикулов
        """
        details = await self.get_tariff_details(session, shop_id)
        return int(round(details.total_per_month))

    @staticmethod
    def get_tariff_for_day(tariff_for_month: float) -> float:
        return round(tariff_for_month / 30, 2)

    async def get_price_for_day_for_shop(
        self,
        session: AsyncSession,
        shop_id: str,
        *,
        leg_latch: LegLatchManager | None = None,
        utc_date: date | None = None,
    ) -> float:
        if leg_latch is None and self._last_explicit_preview_latch is not None:
            leg_latch = self._last_explicit_preview_latch
        if utc_date is None and self._last_explicit_preview_utc_date is not None:
            utc_date = self._last_explicit_preview_utc_date
        leg_latch, utc_date = resolve_tariff_preview_latch_context(
            leg_latch=leg_latch,
            utc_date=utc_date,
        )
        details = await self.get_tariff_details(
            session,
            shop_id,
            leg_latch=leg_latch,
            utc_date=utc_date,
        )
        return details.total_per_day

    async def get_price_for_day_if_enabling_auto_option(
        self,
        session: AsyncSession,
        shop_id: str,
        adv_setting_id: int,
        *,
        override_white_list: bool = False,
        override_target_place: bool = False,
        override_individual_keywords: bool = False,
        leg_latch: LegLatchManager | None = None,
        utc_date: date | None = None,
    ) -> float:
        """Цена за день для магазина при условии включения указанных опций нового тарифа у кампании adv_setting_id."""
        if leg_latch is None and self._last_explicit_preview_latch is not None:
            leg_latch = self._last_explicit_preview_latch
        if utc_date is None and self._last_explicit_preview_utc_date is not None:
            utc_date = self._last_explicit_preview_utc_date
        leg_latch, utc_date = resolve_tariff_preview_latch_context(
            leg_latch=leg_latch,
            utc_date=utc_date,
        )
        details = await self.get_tariff_details(
            session,
            shop_id,
            override_for_adv_id=adv_setting_id,
            override_white_list=override_white_list,
            override_target_place=override_target_place,
            override_individual_keywords=override_individual_keywords,
            leg_latch=leg_latch,
            utc_date=utc_date,
        )
        return details.total_per_day

    async def get_price_for_day_if_enabling_individual_mode(
        self,
        session: AsyncSession,
        shop_id: str,
        adv_setting_id: int,
    ) -> float:
        """Цена за день при включении individual_keywords_target_place_mode у кампании (удобная обёртка)."""
        return await self.get_price_for_day_if_enabling_auto_option(
            session,
            shop_id,
            adv_setting_id,
            override_individual_keywords=True,
        )

    def get_price_for_count_advs_in_cabinet_for_month(
        self, count_advs: int | float, tariff_table: dict[int, int] | None = None
    ) -> float:
        table = tariff_table or self._tariffs
        price_per_adv = self._get_price_per_adv(count_advs, table)
        return price_per_adv * count_advs

    @staticmethod
    def get_payment_for_adv(sum_payment: int, count_advs: int) -> float:
        return sum_payment / count_advs

    async def get_tariff_details(
        self,
        session: AsyncSession,
        shop_id: str,
        *,
        override_for_adv_id: int | None = None,
        override_white_list: bool = False,
        override_target_place: bool = False,
        override_individual_keywords: bool = False,
        leg_latch: LegLatchManager | None = None,
        utc_date: date | None = None,
        cabinet_adv_settings: Sequence[AdvSetting] | None = None,
    ) -> TariffDetails:
        if leg_latch is not None and utc_date is not None:
            self._last_explicit_preview_latch = leg_latch
            self._last_explicit_preview_utc_date = utc_date
        context = await self.calculate_tariff_context(
            session,
            shop_id,
            override_for_adv_id=override_for_adv_id,
            override_white_list=override_white_list,
            override_target_place=override_target_place,
            override_individual_keywords=override_individual_keywords,
            leg_latch=leg_latch,
            utc_date=utc_date,
            cabinet_adv_settings=cabinet_adv_settings,
        )
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
        session: AsyncSession,
        shop_id: str,
        *,
        override_for_adv_id: int | None = None,
        override_white_list: bool = False,
        override_target_place: bool = False,
        override_individual_keywords: bool = False,
        leg_latch: LegLatchManager | None = None,
        utc_date: date | None = None,
        cabinet_adv_settings: Sequence[AdvSetting] | None = None,
    ) -> TariffContext:
        auto_advs = await Pricer.fetch_bot_active_advs(session, shop_id)
        if not auto_advs:
            if override_for_adv_id is not None:
                return TariffContext(count=1, has_auto=True)
            return TariffContext(count=0, has_auto=False)

        def _active(adv: AdvSetting) -> bool:
            use_override = override_for_adv_id is not None and adv.id == override_for_adv_id
            return Pricer.is_part_auto_setting_active(
                adv,
                override_white_list=override_white_list if use_override else False,
                override_target_place=override_target_place if use_override else False,
                override_individual_keywords=override_individual_keywords if use_override else False,
            )

        has_auto = any(_active(adv) for adv in auto_advs)
        if cabinet_adv_settings is None:
            cabinet_adv_settings = await fetch_cabinet_adv_settings_for_metering(
                session, shop_id
            )
        effective_count, _anchors, _billables = await compute_cabinet_billable_units(
            cabinet_adv_settings,
            latch=leg_latch,
            utc_date=utc_date,
        )
        count_value = effective_count
        if has_auto and count_value == 0 and override_for_adv_id is not None:
            if any(adv.id == override_for_adv_id for adv in auto_advs):
                count_value = 1.0

        return TariffContext(count=count_value, has_auto=has_auto)

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
    async def fetch_tariff_auto_advs(
        session: AsyncSession,
        shop_id: str,
        *,
        auto_advs: Sequence[AdvSetting] | None = None,
    ) -> Sequence[AdvSetting]:
        """Возвращает auto-кампании, которые участвуют в тарификации.

        Правило на текущий момент:
        - AdvSetting.bot_active == True
        - Имеет search_adv_id (связь с поисковой кампанией)
        """
        if auto_advs is None:
            auto_advs = await Pricer.fetch_bot_active_advs(session, shop_id)
        if not auto_advs:
            return []

        search_adv_ids = [adv.search_adv_id for adv in auto_advs if adv.search_adv_id]
        if not search_adv_ids:
            return []
        return auto_advs

    @staticmethod
    def is_part_auto_setting_active(
        adv: AdvSetting,
        *,
        override_white_list: bool = False,
        override_target_place: bool = False,
        override_individual_keywords: bool = False,
    ) -> bool:
        if override_white_list or override_target_place or override_individual_keywords:
            return True
        if not adv.bot_active:
            return False
        white_list_active = bool(adv.auto_update_white_list)
        target_place_active = bool(adv.auto_update_target_place)
        individual_keywords_mode_active = bool(adv.individual_keywords_target_place_mode)
        return any(
            [
                white_list_active,
                target_place_active,
                individual_keywords_mode_active,
            ]
        )

    @staticmethod
    def _get_price_per_adv(count_advs: int | float, tariff_table: dict[int, int]) -> float:
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
