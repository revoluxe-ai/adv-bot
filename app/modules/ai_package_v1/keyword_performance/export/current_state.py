"""Current state selector: latest row-coherent daily per campaign identity."""

from __future__ import annotations

from datetime import date

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.domain.enums import (
    BidEvidenceStatus,
    CampaignSlotRole,
    FreshnessStatus,
    KeywordLegRole,
)
from app.modules.ai_package_v1.keyword_performance.domain.models import (
    KeywordCurrentStateRowV1,
    KeywordDailyRowV1,
    RowCoverageV1,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_reader import (
    RawBidDecisionRow,
)
from app.modules.ai_package_v1.keyword_performance.readers.pg_keyword_policy_reader import (
    CampaignPolicySnapshot,
)
from app.modules.ai_package_v1.keyword_performance.readers.pg_keyword_query_policy_reader import (
    KeywordQueryPolicySnapshot,
)


def _slot_role(leg_role: KeywordLegRole) -> CampaignSlotRole:
    if leg_role in (KeywordLegRole.AUTO, KeywordLegRole.SEARCH):
        return CampaignSlotRole.ACTIVE
    if leg_role in (KeywordLegRole.REBOUND_AUTO, KeywordLegRole.REBOUND_SEARCH):
        return CampaignSlotRole.REBOUND_HISTORICAL
    return CampaignSlotRole.AMBIGUOUS


def _freshness_status(
    observation_date: date,
    cutoff: PackageCutoff | None,
) -> FreshnessStatus:
    if cutoff is None:
        return FreshnessStatus.UNKNOWN
    age_days = (cutoff.last_closed_calendar_day - observation_date).days
    if age_days <= 7:
        return FreshnessStatus.FRESH
    return FreshnessStatus.STALE


def _pick_best_daily(
    daily_rows: list[KeywordDailyRowV1],
) -> dict[tuple[int, int, str], KeywordDailyRowV1]:
    """Pick max (date, observation_ts) per (adv_id, nmid, norm_query)."""
    best: dict[tuple[int, int, str], KeywordDailyRowV1] = {}
    for row in daily_rows:
        if row.snapshot_status.value == "AMBIGUOUS":
            continue
        key = (row.adv_id, row.nmid, row.norm_query)
        existing = best.get(key)
        if existing is None:
            best[key] = row
            continue
        if row.date > existing.date:
            best[key] = row
            continue
        if row.date == existing.date:
            row_ts = row.observation_ts or ""
            existing_ts = existing.observation_ts or ""
            if row_ts > existing_ts:
                best[key] = row
    return best


def compute_current_state(
    daily_rows: list[KeywordDailyRowV1],
    *,
    cutoff: PackageCutoff | None = None,
    decisions: dict[tuple[int, int, str], RawBidDecisionRow] | None = None,
    campaign_policies: dict[int, CampaignPolicySnapshot] | None = None,
    query_policies: dict[tuple[int, str], KeywordQueryPolicySnapshot] | None = None,
) -> list[KeywordCurrentStateRowV1]:
    """Pick latest observation per campaign identity with optional enrichments."""
    best = _pick_best_daily(daily_rows)
    decision_map = decisions or {}
    campaign_map = campaign_policies or {}
    query_map = query_policies or {}
    result: list[KeywordCurrentStateRowV1] = []
    for row in sorted(best.values(), key=lambda r: (r.adv_id, r.nmid, r.norm_query)):
        slot = _slot_role(row.leg_role)
        historical_block = None
        if slot == CampaignSlotRole.REBOUND_HISTORICAL:
            historical_block = {
                "physical_adv_id": row.adv_id,
                "leg_role": row.leg_role.value,
            }
        obs_date = date.fromisoformat(row.date)
        freshness = _freshness_status(obs_date, cutoff)

        decision_key = (row.adv_id, row.nmid, row.norm_query)
        decision = decision_map.get(decision_key)
        decision_cpm: float | None = None
        observed: list[str] = []
        missing: list[str] = []
        reason_codes: list[str] = []

        if decision is not None and decision.tuple_variants_at_max_version <= 1:
            if decision.cpm_curr is not None:
                decision_cpm = decision.cpm_curr
                observed.append("decision_cpm_curr")
            else:
                missing.append("decision_cpm_curr")
        else:
            missing.append("decision_cpm_curr")
            if decision is not None and decision.tuple_variants_at_max_version > 1:
                reason_codes.append("SNAPSHOT_CONFLICT")

        configured_max_cpm: float | None = None
        bidder_active: bool | None = None
        campaign_active_status: str | None = None
        strategy_status: str | None = None
        min_target_position: int | None = None
        target_position_mode: str | None = None
        keyword_target_place: int | None = None
        keyword_strategy_mode: str | None = None

        if slot == CampaignSlotRole.ACTIVE and row.adv_setting_id is not None:
            policy = campaign_map.get(row.adv_setting_id)
            if policy is not None:
                configured_max_cpm = policy.configured_max_cpm
                bidder_active = policy.bidder_active
                campaign_active_status = policy.campaign_active_status
                strategy_status = policy.strategy_status
                min_target_position = policy.min_target_position
                target_position_mode = policy.target_position_mode
                if configured_max_cpm is not None:
                    observed.append("configured_max_cpm")
                else:
                    missing.append("configured_max_cpm")
                if strategy_status is not None:
                    observed.append("strategy_status")
                else:
                    missing.append("strategy_status")
            else:
                missing.extend(["configured_max_cpm", "strategy_status"])
            query_policy = query_map.get((row.adv_setting_id, row.norm_query))
            if query_policy is not None:
                keyword_target_place = query_policy.target_place
                keyword_strategy_mode = query_policy.strategy_mode
                if keyword_target_place is not None:
                    observed.append("keyword_target_place")
                else:
                    missing.append("keyword_target_place")
        elif slot == CampaignSlotRole.REBOUND_HISTORICAL:
            missing.extend(
                [
                    "configured_max_cpm",
                    "strategy_status",
                    "keyword_target_place",
                    "current_bid_evidence",
                ]
            )
            reason_codes.append("REBOUND_HISTORICAL_NO_CURRENT_POLICY")

        if row.observation_ts is not None:
            observed.append("observation_ts")
        else:
            missing.append("observation_ts")

        result.append(
            KeywordCurrentStateRowV1(
                shop_id=row.shop_id,
                adv_setting_id=row.adv_setting_id,
                adv_id=row.adv_id,
                leg_role=row.leg_role,
                nmid=row.nmid,
                norm_query=row.norm_query,
                campaign_slot_role=slot,
                observation_date=row.date,
                observation_ts=row.observation_ts,
                freshness_status=freshness.value,
                views=row.views,
                clicks=row.clicks,
                orders=row.orders,
                spend_rub=row.spend_rub,
                cpm=row.cpm,
                cpc=row.cpc,
                ctr=row.ctr,
                cluster_avg_pos=row.cluster_avg_pos,
                observed_cpm=row.cpm,
                configured_max_cpm=configured_max_cpm,
                current_bid_evidence=None,
                current_bid_evidence_status=BidEvidenceStatus.UNAVAILABLE,
                decision_cpm_curr=decision_cpm,
                bidder_active=bidder_active,
                campaign_active_status=campaign_active_status,
                strategy_status=strategy_status,
                min_target_position=min_target_position,
                target_position_mode=target_position_mode,
                keyword_target_place=keyword_target_place,
                keyword_strategy_mode=keyword_strategy_mode,
                last_observed_historical=historical_block,
                row_coverage=RowCoverageV1(
                    observed=tuple(observed),
                    missing=tuple(missing),
                    reason_codes=tuple(reason_codes),
                ),
            )
        )
    return result
