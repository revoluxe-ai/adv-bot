"""Модуль для расчета стоимости тарифов."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum, auto

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def get_price_for_day_if_enabling_auto_option(
        self,
        session: AsyncSession,
        shop_id: str,
        adv_setting_id: int,
        *,
        override_white_list: bool = False,
        override_target_place: bool = False,
        override_individual_keywords: bool = False,
    ) -> float:
        """Цена за день для магазина при условии включения указанных опций нового тарифа у кампании adv_setting_id."""
        details = await self.get_tariff_details(
            session,
            shop_id,
            override_for_adv_id=adv_setting_id,
            override_white_list=override_white_list,
            override_target_place=override_target_place,
            override_individual_keywords=override_individual_keywords,
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
        self, count_advs: int, tariff_table: dict[int, int] | None = None
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
    ) -> TariffDetails:
        context = await self.calculate_tariff_context(
            session,
            shop_id,
            override_for_adv_id=override_for_adv_id,
            override_white_list=override_white_list,
            override_target_place=override_target_place,
            override_individual_keywords=override_individual_keywords,
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
        active_auto_advs = await Pricer.fetch_tariff_auto_advs(
            session, shop_id, auto_advs=auto_advs
        )
        count = len(active_auto_advs)
        if has_auto and count == 0 and override_for_adv_id is not None:
            if any(adv.id == override_for_adv_id for adv in auto_advs):
                count = 1

        return TariffContext(count=count, has_auto=has_auto)

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
        auto_version = adv.automatic_version or 0
        white_list_active = bool(adv.auto_update_white_list)
        target_place_active = bool(adv.auto_update_target_place)
        individual_keywords_mode_active = bool(adv.individual_keywords_target_place_mode)
        if auto_version == 1:
            return any(
                [
                    white_list_active,
                    target_place_active,
                    individual_keywords_mode_active,
                ]
            )
        if auto_version == 2:
            return any(
                [
                    white_list_active,
                    target_place_active,
                    individual_keywords_mode_active,
                ]
            )
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
