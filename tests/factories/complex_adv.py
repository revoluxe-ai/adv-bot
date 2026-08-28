from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from tests.factories import adv_factory
from tests.factories.adv_factory import AdvSettingFactory, KeywordSettingFactory, WBCabinetFactory
from tests.factories.keyword_pipeline import HardStatus, make_calculated_keyword


@dataclass
class ComplexAdvSeed:
    adv_setting: AdvSetting
    search_adv: AdvSetting
    keyword_settings: list[KeywordSetting]
    calculated_keywords: list[CalculatedKeyword]


class _KeywordSpec:
    __slots__ = (
        "status",
        "hard_status",
        "relevant",
        "predict_ctr",
        "predict_ctr_exponent",
        "views",
        "clicks",
        "spend",
        "best",
    )

    def __init__(
        self,
        status: KeywordStatus,
        hard_status: HardStatus,
        relevant: bool,
        predict_ctr: float,
        predict_ctr_exponent: float,
        views: int,
        clicks: int,
        spend: float,
        best: bool = False,
    ) -> None:
        self.status = status
        self.hard_status = hard_status
        self.relevant = relevant
        self.predict_ctr = predict_ctr
        self.predict_ctr_exponent = predict_ctr_exponent
        self.views = views
        self.clicks = clicks
        self.spend = spend
        self.best = best


def _keyword_reason_for_hard_status(hard_status: HardStatus) -> KeywordStatusReason:
    if hard_status == HardStatus.WHITELIST:
        return KeywordStatusReason.WHITE_LIST
    if hard_status == HardStatus.BLACKLIST:
        return KeywordStatusReason.BLACK_LIST
    if hard_status == HardStatus.TURN_OFF:
        return KeywordStatusReason.TURN_OFF
    return KeywordStatusReason.MORE_THEN_HARD_MIN_CTR


def _keyword_spec(index: int) -> _KeywordSpec:
    if index == 0:
        return _KeywordSpec(
            status=KeywordStatus.GOOD,
            hard_status=HardStatus.WHITELIST,
            relevant=True,
            predict_ctr=1.5,
            predict_ctr_exponent=6.0,
            views=1500,
            clicks=200,
            spend=320.0,
            best=True,
        )
    if index < 10:
        return _KeywordSpec(
            status=KeywordStatus.GOOD,
            hard_status=HardStatus.WHITELIST,
            relevant=True,
            predict_ctr=1.2,
            predict_ctr_exponent=5.0,
            views=1200,
            clicks=150,
            spend=210.0,
        )
    if index < 15:
        return _KeywordSpec(
            status=KeywordStatus.BAD,
            hard_status=HardStatus.IN_TEST,
            relevant=True,
            predict_ctr=0.35,
            predict_ctr_exponent=4.0,
            views=800,
            clicks=40,
            spend=45.0,
        )
    if index < 20:
        return _KeywordSpec(
            status=KeywordStatus.GOOD,
            hard_status=HardStatus.IN_TEST,
            relevant=True,
            predict_ctr=1.1,
            predict_ctr_exponent=4.5,
            views=1000,
            clicks=120,
            spend=160.0,
        )
    return _KeywordSpec(
        status=KeywordStatus.BAD,
        hard_status=HardStatus.BLACKLIST,
        relevant=False,
        predict_ctr=0.25,
        predict_ctr_exponent=3.0,
        views=600,
        clicks=30,
        spend=30.0,
    )


def build_complex_keyword_settings(
    adv_setting_id: int,
    *,
    count: int = 50,
) -> list[KeywordSetting]:
    """Создаёт набор KeywordSetting с распределением статусов из complex_adv."""
    adv_factory.fake.unique.clear()
    keyword_settings: list[KeywordSetting] = []

    for idx in range(count):
        ks = KeywordSettingFactory.build(adv_setting_id=adv_setting_id)
        if idx < 10:
            ks.hard_status = HardStatus.WHITELIST
            ks.relevant = True
        elif idx < 20:
            ks.hard_status = HardStatus.IN_TEST
            ks.relevant = True
        else:
            ks.hard_status = HardStatus.BLACKLIST
            ks.relevant = False
        keyword_settings.append(ks)

    return keyword_settings


def build_calculated_keywords(
    adv_setting: AdvSetting,
    keyword_settings: Iterable[KeywordSetting],
) -> list[CalculatedKeyword]:
    """Собирает CalculatedKeyword в том же порядке и со статами что и complex_adv."""
    result: list[CalculatedKeyword] = []
    for idx, ks in enumerate(keyword_settings):
        spec = _keyword_spec(idx)
        calc_keyword = make_calculated_keyword(
            adv_id=adv_setting.adv_id,
            keyword_setting__text=ks.text,
            keyword_setting__hard_status=int(spec.hard_status),
            keyword_setting__relevant=spec.relevant,
            keyword_setting__id=ks.id,
            keyword_setting__predict_ctr=spec.predict_ctr,
            keyword_setting__added_clicks=0,
            cluster_stat__norm_query=ks.text,
            cluster_stat__position=1.0,
            cluster_stat__timestamp=datetime.now(),
            cluster_stat__views=spec.views,
            cluster_stat__clicks=spec.clicks,
            cluster_stat__add_to_cart=0,
            cluster_stat__orders=0,
            cluster_stat__spend=spec.spend,
            cluster_stat__cpc=0,
            cluster_stat__cpm=0.0,
            cluster_stat__base_cart_to_order_conv=0.0,
            cluster_stat__expected_orders_from_cart=0.0,
            cluster_stat__expected_orders=0.0,
            cluster_stat__final_rating=0.0,
            cluster_stat__views_all_time=spec.views,
            cluster_stat__orders_all_time=0,
            state__status=spec.status,
            state__reason=_keyword_reason_for_hard_status(spec.hard_status),
            state__best_keyword_status=spec.best,
        )
        result.append(calc_keyword)
    return result


async def create_complex_adv_seed(session: AsyncSession) -> ComplexAdvSeed:
    """Создаёт тот же набор объектов, который раньше строился прямо в conftest."""
    # Попробуем переиспользовать существующий кабинет из seed-а
    existing = await session.execute(
        select(WBCabinet).where(WBCabinet.shop_id == "test_shop_id")
    )
    wb_cabinet: WBCabinet | None = existing.scalar_one_or_none()
    if wb_cabinet is None:
        # Не используем factory Sequence для ``id``: при полном pytest-ране
        # в БД могут оставаться записи от других DB-тестов, и фиксированный
        # ``1_000_000 + n`` даёт ложные UniqueViolation до очистки.
        wb_cabinet = WBCabinet(
            shop_id="test_shop_id",
            active=True,
            balance=0.0,
            bonus=0.0,
            demo=True,
            expiration_time=datetime.now() + timedelta(days=7),
        )
        session.add(wb_cabinet)
        await session.flush()
        await session.refresh(wb_cabinet)

    adv_setting = AdvSettingFactory.build(
        adv_id=123,
        wb_cabinet_id=wb_cabinet.id, # Используем ID созданного WBCabinet
        nmids=[456],
        auto_update_white_list=True,
        auto_update_target_place=True,
        auto_update_exponent=True,
        auto_add_only_relevant_phrase=False,
        bidder_for_auto=True,
        bidder_active=True,
    )
    adv_setting.cpm = 100
    adv_setting.max_cpm = 250
    adv_setting.max_place = 120
    adv_setting.exponent_predict_ctr = 8.0

    search_adv = AdvSettingFactory.build()
    search_adv.cpm = 90
    adv_setting._search_adv = search_adv.adv_id

    session.add(adv_setting)
    await session.flush()
    await session.refresh(adv_setting)

    keyword_settings = build_complex_keyword_settings(adv_setting.id)
    session.add_all(keyword_settings)
    await session.flush()
    for ks in keyword_settings:
        await session.refresh(ks)

    calculated_keywords = build_calculated_keywords(adv_setting, keyword_settings)

    return ComplexAdvSeed(
        adv_setting=adv_setting,
        search_adv=search_adv,
        keyword_settings=keyword_settings,
        calculated_keywords=calculated_keywords,
    )
