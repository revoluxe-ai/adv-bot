"""Per-tick маршрутизация collection ownership для campaign grains.

Spec: ``connected-shop-campaign-ad-data-collection`` (design §B.1, §B.2).
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.
Decision: ``openspec/changes/shop-wide-campaign-data-collection/decisions/shop-runner-shop-wide-collection/decision.md``.

Задача 3.1. Чистый domain-resolver: принимает WB discovery и universe loader'а
``get_complex_advs(only_bot_active=False)`` без PG/CH/WB side effects. Grains:
``full_adv_wb_stat`` и managed-only ``clusters_adv_stats``. ``wb_common_stat`` и
funnel ``(nmid, date)`` **вне** scope — owner ``shop-wide-common-sales-collection``.

``bot_active`` и наличие ``AdvSetting`` alone **не** используются как surrogate
management connect; ownership только через loader predicate §B.1.
``UNKNOWN`` — fail-closed, не означает enrollment в управление.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)


class CollectionRoute(str, Enum):
    """Маршрут сбора fact grain для одной WB physical campaign id."""

    MANAGED = "managed"
    UNMANAGED = "unmanaged"
    UNKNOWN = "unknown"


class CampaignCollectionGrain(str, Enum):
    """Campaign advertising grains, поддерживаемые resolver 3.1."""

    FULL_ADV_WB_STAT = "full_adv_wb_stat"
    CLUSTERS_ADV_STATS = "clusters_adv_stats"


# Явные reason codes для inventory/availability (задачи 3.8+).
REASON_MANAGED_LOADER_OWNERSHIP = "managed_loader_ownership"
REASON_UNMANAGED_WB_DISCOVERY = "unmanaged_wb_discovery"
REASON_UNKNOWN_NOT_CLASSIFIED = "unknown_not_classified"
REASON_UNKNOWN_CLUSTERS_OUTSIDE_MANAGED = "unknown_clusters_outside_managed"
REASON_UNSUPPORTED_GRAIN = "unsupported_grain"


@dataclass(frozen=True, slots=True)
class CampaignRouteKey:
    """Ключ маршрута per shop tick."""

    shop_id: str
    wb_adv_id: int
    grain: CampaignCollectionGrain


@dataclass(frozen=True, slots=True)
class CampaignRouteDecision:
    """Детерминированное решение resolver для одного ключа."""

    key: CampaignRouteKey
    route: CollectionRoute
    reason_code: str


@dataclass(frozen=True, slots=True)
class RouteResolverTickInput:
    """Вход resolver на один shop tick.

    ``loader_complex_advs`` — post-filter ``get_complex_advs``: только строки с
    непустыми ``nmids``, ``only_bot_active=False`` (``refused`` включён, ``done``
    отсутствует). Search legs учитываются через ``ComplexAdv.all_adv_ids``.
    ``wb_discovered_adv_ids`` — physical ids из WB discovery для ``shop_id``.
    """

    shop_id: str
    wb_discovered_adv_ids: frozenset[int]
    loader_complex_advs: tuple[ComplexAdv, ...]


@dataclass(frozen=True, slots=True)
class RouteResolverTickResult:
    """Полный набор решений за tick для union managed ∪ discovered ids."""

    shop_id: str
    managed_ownership_adv_ids: frozenset[int]
    decisions: tuple[CampaignRouteDecision, ...]

    def decision_for(
        self, wb_adv_id: int, grain: CampaignCollectionGrain
    ) -> CampaignRouteDecision | None:
        """Найти решение по ``(wb_adv_id, grain)`` или ``None`` если ключ не строился."""
        for item in self.decisions:
            if item.key.wb_adv_id == wb_adv_id and item.key.grain is grain:
                return item
        return None

    def routes_by_grain(
        self, grain: CampaignCollectionGrain
    ) -> Mapping[int, CollectionRoute]:
        """Словарь ``wb_adv_id → route`` для одного grain."""
        return {
            item.key.wb_adv_id: item.route
            for item in self.decisions
            if item.key.grain is grain
        }


def build_managed_ownership_adv_ids(
    loader_complex_advs: Iterable[ComplexAdv],
) -> frozenset[int]:
    """Ownership set §B.1 для ``full_adv_wb_stat`` и ``clusters_adv_stats``.

    Объединение ``all_adv_ids`` каждого ``ComplexAdv`` из loader'а: parent +
    search leg при загруженном ``search_adv``.
    """
    owned: set[int] = set()
    for complex_adv in loader_complex_advs:
        owned.update(int(adv_id) for adv_id in complex_adv.all_adv_ids)
    return frozenset(owned)


class CampaignCollectionRouteResolver:
    """Классифицирует collection ownership per ``(shop_id, wb_adv_id, grain)``.

    Детерминирован и без side effects. Не читает ``bot_active`` отдельно от
    уже отфильтрованного loader input и не создаёт management enrollment.
    """

    _SUPPORTED_GRAINS: frozenset[CampaignCollectionGrain] = frozenset(
        CampaignCollectionGrain
    )

    def resolve_route(
        self,
        *,
        shop_id: str,
        wb_adv_id: int,
        grain: CampaignCollectionGrain,
        wb_discovered_adv_ids: frozenset[int],
        managed_ownership_adv_ids: frozenset[int],
    ) -> CampaignRouteDecision:
        """Одно решение для physical ``wb_adv_id`` и campaign grain."""
        key = CampaignRouteKey(shop_id=shop_id, wb_adv_id=wb_adv_id, grain=grain)
        if grain not in self._SUPPORTED_GRAINS:
            return CampaignRouteDecision(
                key=key,
                route=CollectionRoute.UNKNOWN,
                reason_code=REASON_UNSUPPORTED_GRAIN,
            )

        if wb_adv_id in managed_ownership_adv_ids:
            return CampaignRouteDecision(
                key=key,
                route=CollectionRoute.MANAGED,
                reason_code=REASON_MANAGED_LOADER_OWNERSHIP,
            )

        if grain is CampaignCollectionGrain.CLUSTERS_ADV_STATS:
            return CampaignRouteDecision(
                key=key,
                route=CollectionRoute.UNKNOWN,
                reason_code=REASON_UNKNOWN_CLUSTERS_OUTSIDE_MANAGED,
            )

        if wb_adv_id in wb_discovered_adv_ids:
            return CampaignRouteDecision(
                key=key,
                route=CollectionRoute.UNMANAGED,
                reason_code=REASON_UNMANAGED_WB_DISCOVERY,
            )

        return CampaignRouteDecision(
            key=key,
            route=CollectionRoute.UNKNOWN,
            reason_code=REASON_UNKNOWN_NOT_CLASSIFIED,
        )

    def resolve_tick(self, tick_input: RouteResolverTickInput) -> RouteResolverTickResult:
        """Построить решения для всех ids, релевантных shop tick."""
        managed_ids = build_managed_ownership_adv_ids(tick_input.loader_complex_advs)
        candidate_ids = managed_ids | tick_input.wb_discovered_adv_ids
        decisions: list[CampaignRouteDecision] = []
        for wb_adv_id in sorted(candidate_ids):
            for grain in CampaignCollectionGrain:
                decisions.append(
                    self.resolve_route(
                        shop_id=tick_input.shop_id,
                        wb_adv_id=wb_adv_id,
                        grain=grain,
                        wb_discovered_adv_ids=tick_input.wb_discovered_adv_ids,
                        managed_ownership_adv_ids=managed_ids,
                    )
                )
        return RouteResolverTickResult(
            shop_id=tick_input.shop_id,
            managed_ownership_adv_ids=managed_ids,
            decisions=tuple(decisions),
        )

    @staticmethod
    def is_management_relationship_proven(_decision: CampaignRouteDecision) -> bool:
        """Management relationship не доказывается на слое routing (design §B.3, S21).

        Collection route ``MANAGED`` означает только loader ownership §B.1, не user connect.
        """
        return False

    @staticmethod
    def is_managed_collector_write_eligible(decision: CampaignRouteDecision) -> bool:
        """Managed legacy collector MAY писать только при route ``MANAGED``."""
        return decision.route is CollectionRoute.MANAGED

    @staticmethod
    def is_unmanaged_collector_write_eligible(decision: CampaignRouteDecision) -> bool:
        """Unmanaged collector MAY писать только ``UNMANAGED`` ``full_adv_wb_stat`` (S09).

        Managed ownership в том же tick блокирует unmanaged write eligibility для grain.
        """
        return (
            decision.route is CollectionRoute.UNMANAGED
            and decision.key.grain is CampaignCollectionGrain.FULL_ADV_WB_STAT
        )

    @classmethod
    def from_loader_and_discovery(
        cls,
        *,
        shop_id: str,
        wb_discovered_adv_ids: Iterable[int],
        loader_complex_advs: Sequence[ComplexAdv],
    ) -> RouteResolverTickResult:
        """Удобный фасад: собрать ``RouteResolverTickInput`` и вызвать ``resolve_tick``."""
        tick_input = RouteResolverTickInput(
            shop_id=shop_id,
            wb_discovered_adv_ids=frozenset(int(adv_id) for adv_id in wb_discovered_adv_ids),
            loader_complex_advs=tuple(loader_complex_advs),
        )
        return cls().resolve_tick(tick_input)
