"""
Shop-runner hook: read-only V1 hierarchical diagnostics.

Один supplier-orders сбор на магазин и закрытое окно, spend по inventory,
campaign economics через AttributionFactsReader. Не вызывает Apply и не пишет WB.
"""

from __future__ import annotations

import logging
from datetime import datetime
from collections.abc import Sequence
from zoneinfo import ZoneInfo

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    ControlPathKind,
    HierarchicalEnrollment,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.resolver_models import ResolverContext
from app.modules.ad_control_settings.persistence.repository import (
    AdControlSettingsRepository,
)
from app.modules.ad_control_settings.runtime.evaluation import (
    ShopEvaluationRequest,
    ShopEvaluationResult,
    evaluate_shop_window,
    select_campaign_ids,
)
from app.modules.ad_control_settings.runtime.providers import (
    FullAdvShopSpend,
    HistoryThenInventoryAdvIds,
    ReportsManagerOrdersAdapter,
    SupplierOrdersClient,
)
from app.modules.ad_control_settings.runtime.shop_order_gmv import as_moscow
from app.modules.attribution_facts.domain.models import (
    AttributionQueryResult,
    AttributionScope,
    DateWindow,
)
from app.modules.attribution_facts.readers.ch_attribution_facts_reader import (
    ChAttributionFactsReader,
)
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.session_maker import get_async_session_maker

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_DAYS = 7
_MOSCOW = ZoneInfo("Europe/Moscow")


class _ClosedPort:
    """Фейковый порт: неenrolled путь не должен читать факты."""

    async def get_supplier_orders(
        self,
        *,
        date_from: str,
        flag: int = 0,
    ) -> Sequence[object]:
        raise RuntimeError("supplier orders are shop-scoped and enrollment-gated")

    async def sum_spend_by_adv(
        self,
        adv_ids: tuple[int, ...],
        window: DateWindow,
    ) -> None:
        raise RuntimeError("shop spend is enrollment-gated")

    async def query(
        self,
        scope: AttributionScope,
        window: DateWindow,
    ) -> AttributionQueryResult:
        raise RuntimeError("attribution read is enrollment-gated")


def default_closed_window(now: datetime) -> DateWindow:
    """Последние 7 закрытых календарных дней Europe/Moscow, конец — вчера."""
    day = as_moscow(now).date()
    end = day.fromordinal(day.toordinal() - 1)
    start = end.fromordinal(end.toordinal() - (DEFAULT_WINDOW_DAYS - 1))
    return DateWindow(start=start, end=end)


async def run_enabled_shop_diagnostics(
    *,
    shop_id: str,
    reports_manager: SupplierOrdersClient,
    now: datetime | None = None,
) -> ShopEvaluationResult:
    """
    Снять диагностику магазина.

    Магазин считается enrolled для этого read-only тика, только если слот
    DRR_POLICY включён и несёт payload. Иначе supplier orders не читаются.
    """
    moment = now if now is not None else datetime.now(_MOSCOW)
    window = default_closed_window(moment)
    async with get_async_session_maker(read_only=True) as session:
        repository = AdControlSettingsRepository(session)
        shop_features = await repository.load_shop_slots(shop_id)
        drr = shop_features.get(AdControlFeatureId.DRR_POLICY)
        if (
            drr is None
            or drr.activation != ShopFeatureActivation.ENABLED
            or not isinstance(drr.payload, DrrPolicyParamsV1)
        ):
            result = await evaluate_shop_window(
                ShopEvaluationRequest(
                    shop_id=shop_id,
                    window=window,
                    collected_at=moment,
                    enrolled=False,
                ),
                orders=_ClosedPort(),
                spend=_ClosedPort(),
                attribution=_ClosedPort(),
            )
            _log(shop_id, window, result)
            return result
        target = drr.payload.profile.target_drr_percent
        async with get_clickhouse_client() as client:
            history_ids = await HistoryThenInventoryAdvIds(
                client,
                source="history",
            ).list_adv_ids(shop_id)
            inventory_ids = await HistoryThenInventoryAdvIds(
                client,
                source="inventory",
            ).list_adv_ids(shop_id)
            campaign_ids = select_campaign_ids(history_ids, inventory_ids)
            contexts: list[ResolverContext] = []
            for advert_id in campaign_ids:
                campaign = CampaignRef(shop_id=shop_id, advert_id=advert_id)
                campaign_features = await repository.load_campaign_slots(campaign)
                contexts.append(
                    ResolverContext(
                        enrollment=HierarchicalEnrollment.ENROLLED,
                        control_path=ControlPathKind.HIERARCHICAL,
                        shop_id=shop_id,
                        shop_features=shop_features,
                        campaign=campaign,
                        campaign_features=campaign_features,
                    )
                )
            result = await evaluate_shop_window(
                ShopEvaluationRequest(
                    shop_id=shop_id,
                    window=window,
                    collected_at=moment,
                    enrolled=True,
                    contexts=tuple(contexts),
                    inventory_adv_ids=inventory_ids,
                    shop_target_drr_percent=target,
                ),
                orders=ReportsManagerOrdersAdapter(reports_manager),
                spend=FullAdvShopSpend(client),
                attribution=ChAttributionFactsReader(client),
            )
            _log(shop_id, window, result)
            return result


def _log(shop_id: str, window: DateWindow, result: ShopEvaluationResult) -> None:
    gmv_status = None if result.gmv is None else result.gmv.status.value
    logger.info(
        "hierarchical ad-control diagnostics shop_id=%s window=%s/%s "
        "collections=%s gmv_status=%s reports=%s reasons=%s",
        shop_id,
        window.start.isoformat(),
        window.end.isoformat(),
        result.supplier_order_collections,
        gmv_status,
        len(result.reports),
        ",".join(code.value for code in result.reason_codes),
    )
