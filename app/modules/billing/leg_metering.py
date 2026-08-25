"""Fair leg-pause billing: якорь комплекта, веса слотов Auto/Search, effective_count.

Связь с доменом: честное дневное списание по active_status ног WB (spec
billing-fair-leg-pause). Якорь — строка с bot_active и привязкой search_adv_id,
не WB marketing type.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.leg_latch import AdvPaymentLegSlot, LegLatchManager
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

_STARTED = "started"
_SLOT_WEIGHT = 0.5


@dataclass(frozen=True, slots=True)
class MeteringAnchor:
    """Якорная авто-настройка и опциональная связанная Search-строка."""

    anchor: AdvSetting
    search_row: AdvSetting | None


@dataclass(frozen=True, slots=True)
class AnchorBillable:
    """Billable веса слотов якоря за UTC-день (после latch или instant)."""

    anchor_id: int
    auto_weight: float
    search_weight: float
    has_search_slot: bool

    @property
    def total(self) -> float:
        return self.auto_weight + (
            self.search_weight if self.has_search_slot else 0.0
        )


def instant_leg_weight(active_status: str | None) -> float:
    """Мгновенный вес слота: started → 0.5, иначе 0 (spec per-leg daily slot weights)."""
    return _SLOT_WEIGHT if active_status == _STARTED else 0.0


def instant_anchor_weights(anchor: MeteringAnchor) -> tuple[float, float | None]:
    """Instant веса Auto и Search (Search None если слота нет)."""
    auto_w = instant_leg_weight(anchor.anchor.active_status)
    if anchor.search_row is None:
        return auto_w, None
    return auto_w, instant_leg_weight(anchor.search_row.active_status)


def resolve_metering_anchors(adv_settings: Sequence[AdvSetting]) -> list[MeteringAnchor]:
    """Определить якоря биллинга по search_adv_id и bot_active (design §Якорь).

    Search-строка (adv_id на которую ссылается чужой search_adv_id) никогда
    не является якорем.
    """
    by_adv_id: dict[int, AdvSetting] = {adv.adv_id: adv for adv in adv_settings}
    referenced_search_adv_ids: set[int] = {
        adv.search_adv_id
        for adv in adv_settings
        if adv.search_adv_id is not None
    }
    anchors: list[MeteringAnchor] = []
    for adv in adv_settings:
        if not adv.bot_active:
            continue
        if adv.adv_id in referenced_search_adv_ids:
            continue
        search_row: AdvSetting | None = None
        if adv.search_adv_id is not None:
            search_row = by_adv_id.get(adv.search_adv_id)
        anchors.append(MeteringAnchor(anchor=adv, search_row=search_row))
    return anchors


async def fetch_cabinet_adv_settings_for_metering(
    session: AsyncSession, shop_id: str
) -> Sequence[AdvSetting]:
    """Все AdvSetting кабинета для резолва пары якорь/Search (batch-read)."""
    stmt = (
        select(AdvSetting)
        .join(AdvSetting.wb_cabinet)
        .where(WBCabinet.shop_id == shop_id)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def record_anchor_latch_samples(
    anchors: Sequence[MeteringAnchor],
    latch: LegLatchManager,
    utc_date: date,
) -> None:
    """Накопить max instant-веса в latch за UTC-день (L3 anti-gaming)."""
    for item in anchors:
        auto_w, search_w = instant_anchor_weights(item)
        _ = await latch.record_sample(
            item.anchor.id, AdvPaymentLegSlot.AUTO_LEG, auto_w, utc_date
        )
        if item.search_row is not None and search_w is not None:
            _ = await latch.record_sample(
                item.anchor.id, AdvPaymentLegSlot.SEARCH_LEG, search_w, utc_date
            )


async def compute_anchor_billables(
    anchors: Sequence[MeteringAnchor],
    *,
    latch: LegLatchManager | None = None,
    utc_date: date | None = None,
) -> list[AnchorBillable]:
    """Billable веса по якорям.

    Без latch — только instant (active_status). С latch и utc_date — max(latch_read,
    instant) на слот: preview не пишет в Redis, но не скрывает started ноги при
    пустом latch; charge после record_anchor_latch_samples получает тот же результат.
    """
    billables: list[AnchorBillable] = []
    for item in anchors:
        has_search = item.search_row is not None
        instant_auto, instant_search = instant_anchor_weights(item)
        if latch is not None and utc_date is not None:
            latch_auto = await latch.get_billable_weight(
                item.anchor.id, AdvPaymentLegSlot.AUTO_LEG, utc_date
            )
            auto_w = max(latch_auto, instant_auto)
            search_w = 0.0
            if has_search and instant_search is not None:
                latch_search = await latch.get_billable_weight(
                    item.anchor.id, AdvPaymentLegSlot.SEARCH_LEG, utc_date
                )
                search_w = max(latch_search, instant_search)
        else:
            auto_w = instant_auto
            search_w = instant_search if instant_search is not None else 0.0
        billables.append(
            AnchorBillable(
                anchor_id=item.anchor.id,
                auto_weight=auto_w,
                search_weight=search_w,
                has_search_slot=has_search,
            )
        )
    return billables


def effective_count_from_billables(billables: Sequence[AnchorBillable]) -> float:
    """Сумма платных единиц слотов кабинета (0.5 + 0.5 = 1.0)."""
    return sum(b.total for b in billables)


async def compute_cabinet_billable_units(
    adv_settings: Sequence[AdvSetting],
    *,
    latch: LegLatchManager | None = None,
    utc_date: date | None = None,
) -> tuple[float, list[MeteringAnchor], list[AnchorBillable]]:
    """Единая точка расчёта effective_count для Pricer и billing charge."""
    anchors = resolve_metering_anchors(adv_settings)
    billables = await compute_anchor_billables(
        anchors, latch=latch, utc_date=utc_date
    )
    return effective_count_from_billables(billables), anchors, billables
