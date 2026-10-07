"""Enrich raw CH daily rows → KeywordDailyRowV1 with scope + derived metrics."""

from __future__ import annotations

from app.modules.ai_package_v1.keyword_performance.domain.derived_metrics import (
    finite_or_none,
    safe_cpo,
    safe_ratio,
)
from app.modules.ai_package_v1.keyword_performance.domain.enums import (
    KeywordLegRole,
    KeywordReasonCode,
    RawQueryStatus,
    SnapshotStatus,
)
from app.modules.ai_package_v1.keyword_performance.domain.models import (
    KeywordDailyRowV1,
    RowCoverageV1,
)
from app.modules.ai_package_v1.keyword_performance.domain.spend_mapper import map_spend
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_daily_reader import (
    RawDailySnapshotRow,
)
from app.modules.ai_package_v1.keyword_performance.scope.adv_id_collector import (
    assignment_for_adv_id,
)
from app.modules.ai_package_v1.keyword_performance.scope.dto import KeywordExportScope


def assemble_daily_rows(
    raw_rows: list[RawDailySnapshotRow],
    *,
    manifest_shop_id: str,
    scope: KeywordExportScope,
) -> list[KeywordDailyRowV1]:
    """Transform raw CH rows into canonical daily facts."""
    result: list[KeywordDailyRowV1] = []
    for raw in raw_rows:
        assignment = assignment_for_adv_id(scope, raw.adv_id)
        leg_role = KeywordLegRole.AMBIGUOUS
        adv_setting_id: int | None = None
        reason_codes: list[str] = []
        if assignment is not None:
            try:
                leg_role = KeywordLegRole(assignment.leg_role)
            except ValueError:
                leg_role = KeywordLegRole.AMBIGUOUS
            if assignment.ambiguous_ownership or assignment.foreign_shop:
                reason_codes.append(KeywordReasonCode.AMBIGUOUS_OWNERSHIP.value)
                adv_setting_id = None
            else:
                adv_setting_id = assignment.adv_setting_id
            if assignment.ambiguous_leg:
                reason_codes.append(KeywordReasonCode.AMBIGUOUS_LEG.value)

        if raw.snapshot_variants_at_max_ts > 1:
            reason_codes.append(KeywordReasonCode.SNAPSHOT_CONFLICT.value)
            result.append(
                KeywordDailyRowV1(
                    shop_id=manifest_shop_id,
                    adv_setting_id=adv_setting_id,
                    adv_id=raw.adv_id,
                    leg_role=leg_role,
                    nmid=raw.nmid,
                    norm_query=raw.norm_query,
                    raw_query=None,
                    raw_query_status=RawQueryStatus.RAW_QUERY_UNAVAILABLE,
                    date=raw.stat_date.isoformat(),
                    snapshot_status=SnapshotStatus.AMBIGUOUS,
                    row_coverage=RowCoverageV1(
                        missing=tuple(
                            "views,clicks,add_to_cart,orders,spend,cpm,cpc,avr_pos,ctr".split(
                                ","
                            )
                        ),
                        reason_codes=tuple(reason_codes),
                    ),
                )
            )
            continue

        spend_rub, spend_status = map_spend(raw.spend)
        views = raw.views
        clicks = raw.clicks
        add_to_cart = raw.add_to_cart
        orders = raw.orders
        observed: list[str] = []
        missing: list[str] = []
        for name, val in (
            ("views", views),
            ("clicks", clicks),
            ("add_to_cart", add_to_cart),
            ("orders", orders),
            ("spend_rub", spend_rub),
            ("cpm", raw.cpm),
            ("cpc", raw.cpc),
            ("cluster_avg_pos", raw.avr_pos),
        ):
            if val is None:
                missing.append(name)
            else:
                observed.append(name)

        ctr = safe_ratio(clicks, views)
        if raw.ctr is not None and ctr is None:
            ctr = finite_or_none(raw.ctr)

        obs_ts = (
            raw.last_snapshot_ts.isoformat()
            if raw.last_snapshot_ts is not None
            else None
        )
        result.append(
            KeywordDailyRowV1(
                shop_id=manifest_shop_id,
                adv_setting_id=adv_setting_id,
                adv_id=raw.adv_id,
                leg_role=leg_role,
                nmid=raw.nmid,
                norm_query=raw.norm_query,
                raw_query=None,
                raw_query_status=RawQueryStatus.RAW_QUERY_UNAVAILABLE,
                date=raw.stat_date.isoformat(),
                observation_ts=obs_ts,
                views=views,
                clicks=clicks,
                add_to_cart=add_to_cart,
                orders=orders,
                spend_rub=spend_rub,
                query_spend_status=spend_status,
                cpm=finite_or_none(raw.cpm),
                cpc=finite_or_none(raw.cpc),
                ctr=ctr,
                conv_views_to_cart=safe_ratio(add_to_cart, views),
                conv_cart_to_order=safe_ratio(orders, add_to_cart),
                conv_views_to_order=safe_ratio(orders, views),
                cpo_rub=safe_cpo(
                    spend_rub, orders, spend_factual=spend_status.value == "FACTUAL"
                ),
                cluster_avg_pos=finite_or_none(raw.avr_pos),
                snapshot_status=SnapshotStatus.OK,
                row_coverage=RowCoverageV1(
                    observed=tuple(observed),
                    missing=tuple(missing),
                    reason_codes=tuple(reason_codes),
                ),
            )
        )
    return result
