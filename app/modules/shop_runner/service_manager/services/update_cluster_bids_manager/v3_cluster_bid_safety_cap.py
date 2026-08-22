"""V3 safety cap для ``update_cluster_bids``: при overspend (fact CPO > max CPO) ограничить исходящую cluster bid матричной ставкой текущего V3-state.

Overspend gate читает ``fact_datas`` / ``plan_datas`` по **Auto** ``auto_adv_id``;
WB/Redis и ``NewBid.adv_id`` — по **Search** ``adv_id``.
``reference_bid`` — приоритет ``cluster-bid`` Redis (как UI ``cpm_set_bid``), не stats CPM.
Cap pass не пишет в Redis; ``remember_bids`` только после успешного WB в ``_apply_command``.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from app.modules.cluster_bids_redis import ClusterBidKey
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    aggression_target_for_stored_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
    build_keyword_v3_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
    state_candidates_by_mode_for_ctx,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.mappers.adv_id_item_map import (
    AdvIdItemCalculateData,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.calculation_input import (
    CalculationInput,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import (
    DirectEnum,
    NewBid,
    UpdateBidsCommand,
)
from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
    load_campaign_orders_per_cart_7d,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from .cluster_bid_trace import (
    is_trace_cell,
    is_trace_enabled,
    log_cluster_bid_trace,
    trace_target_defaults,
)
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import (
    BidderKeywordStatus,
)

if TYPE_CHECKING:
    from app.core.mp.wb.dto import AdvMinNmidsBids
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
        ComplexAdv,
    )

logger = logging.getLogger(__name__)

CellKey = tuple[int, int, str]
_PREDICT_PROFILES_MAX_CONCURRENT = 16


def _cap_direct_vs_baseline(*, outgoing_bid: int, baseline_bid: int) -> DirectEnum:
    """Направление cap-clamp относительно ставки, которую реально меняем (candidate / reference)."""
    if outgoing_bid < baseline_bid:
        return DirectEnum.DOWN
    if outgoing_bid > baseline_bid:
        return DirectEnum.UP
    return DirectEnum.DOWN


def resolve_reference_bid_for_cap(
    *,
    search_adv_id: int,
    nmid: int,
    cluster: str,
    stored_bids: dict[ClusterBidKey, int],
    keyword: CalculatedKeyword | None,
    calculation_input: CalculationInput | None,
) -> int | None:
    """Эталон «текущей» ставки для cap pass (не stats-only).

    Приоритет: ``cluster-bid`` Redis → ``keyword.cpm_set_bid`` → ``CalculationInput.current_bid``.
    """
    key = ClusterBidKey(search_adv_id=search_adv_id, nmid=nmid, cluster=cluster)
    stored = stored_bids.get(key)
    if stored is not None:
        return stored
    if keyword is not None and keyword.cpm_set_bid is not None:
        return int(keyword.cpm_set_bid)
    if calculation_input is not None:
        return calculation_input.current_bid
    return None


def _overspend_reason(
    auto_adv_id: int,
    fact_datas: dict[int, FactData],
    plan_datas: dict[int, PlanData],
) -> str | None:
    """Вернуть skip-reason или ``None``, если overspend активен."""
    fact = fact_datas.get(auto_adv_id)
    if fact is None or fact.pay_for_order is None:
        return "missing_fact_cpo"
    plan = plan_datas.get(auto_adv_id)
    if plan is None:
        return "missing_max_cpo"
    if float(fact.pay_for_order) <= float(plan.max_pay_for_order):
        return "overspend_false"
    return None


def _matrix_cap_for_ctx(
    ctx: KeywordV3Context,
    ladder_inputs: LadderInputs,
    strategy_mode: KeywordStrategyMode,
) -> int | None:
    """Матричная ставка V3-state (``ModeCandidate.bid``) для текущего ``strategy_mode``."""
    aggression = aggression_target_for_stored_mode(strategy_mode)
    if aggression is None:
        return None
    candidates = state_candidates_by_mode_for_ctx(ctx, ladder_inputs)
    candidate = candidates.get(aggression)
    if candidate is None or not candidate.is_valid or candidate.bid is None:
        return None
    return int(round(float(candidate.bid)))


async def build_keywords_by_cell(
    advs: list[ComplexAdv],
    map_datas: set[AdvIdItemCalculateData],
    keywords_getter: Callable[[ComplexAdv], Awaitable[list[CalculatedKeyword]]],
) -> dict[CellKey, CalculatedKeyword]:
    """Индекс ключей по ячейке карты для ``resolve_reference_bid_for_cap``."""
    adv_by_auto_id = {adv.adv_id: adv for adv in advs}
    cells_by_auto: dict[int, set[AdvIdItemCalculateData]] = {}
    for cell in map_datas:
        if not cell.v3_managed:
            continue
        cells_by_auto.setdefault(cell.adv_id, set()).add(cell)

    result: dict[CellKey, CalculatedKeyword] = {}
    for auto_adv_id, cells in cells_by_auto.items():
        adv = adv_by_auto_id.get(auto_adv_id)
        if adv is None:
            continue
        keywords = await keywords_getter(adv)
        kw_by_ks_id = {kw.keyword_setting_original_id: kw for kw in keywords}
        for cell in cells:
            kw = kw_by_ks_id.get(cell.keyword_setting_original_id)
            if kw is not None:
                result[(cell.search_adv_id, cell.nmid, cell.cluster)] = kw
    return result


async def build_v3_matrix_cap_index(
    advs: list[ComplexAdv],
    map_datas: set[AdvIdItemCalculateData],
    min_bids: AdvMinNmidsBids,
    keywords_getter: Callable[[ComplexAdv], Awaitable[list[CalculatedKeyword]]],
) -> dict[CellKey, int]:
    """Построить индекс cap bid по ячейкам V3 (Search adv_id × nmid × cluster)."""
    adv_by_auto_id = {adv.adv_id: adv for adv in advs if adv.bot_active}
    cells_by_adv_id: dict[int, list[AdvIdItemCalculateData]] = {}
    for cell in map_datas:
        if not cell.v3_managed or cell.adv_id not in adv_by_auto_id:
            continue
        cells_by_adv_id.setdefault(cell.adv_id, []).append(cell)

    if not cells_by_adv_id:
        return {}

    predictor = build_predict_keywords_target_place()
    cap_index: dict[CellKey, int] = {}
    sem = asyncio.Semaphore(_PREDICT_PROFILES_MAX_CONCURRENT)

    async def _load_profile(
        nmid_: int, min_bid_: int
    ) -> tuple[int, dict[str, list[BidPosition]]]:
        async with sem:
            profiles_ = await predictor.load_bid_profiles_for_nmid(
                nmid=nmid_,
                min_bid=min_bid_,
                positions_size=300,
            )
            return nmid_, profiles_

    for adv_id, cells in cells_by_adv_id.items():
        adv = adv_by_auto_id[adv_id]
        keywords = await keywords_getter(adv)
        campaign_opc = await load_campaign_orders_per_cart_7d(adv.adv_setting)

        nmids = {cell.nmid for cell in cells}
        profile_tasks: list[Awaitable[tuple[int, dict[str, list[BidPosition]]]]] = []
        nmid_list: list[int] = []
        for nmid in nmids:
            try:
                min_bid = min_bids.search[nmid]
            except KeyError:
                logger.error(
                    "v3_cap_index: нет min_bid для nmid=%s (adv_id=%s)",
                    nmid,
                    adv_id,
                )
                continue
            nmid_list.append(nmid)
            profile_tasks.append(_load_profile(nmid, min_bid))

        raw_profiles_by_nmid: dict[int, dict[str, list[BidPosition]]] = {}
        if profile_tasks:
            profile_results: list[tuple[int, dict[str, list[BidPosition]]] | BaseException] \
                = await asyncio.gather(
                *profile_tasks, return_exceptions=True
            )
            for nmid, item in zip(nmid_list, profile_results, strict=False):
                if isinstance(item, BaseException):
                    logger.error(
                        "v3_cap_index: ошибка профиля nmid=%s adv_id=%s: %s",
                        nmid,
                        adv_id,
                        item,
                    )
                    continue
                profiles: dict[str, list[BidPosition]]= item[1]
                raw_profiles_by_nmid[nmid] = profiles

        cells_by_nmid: dict[int, list[AdvIdItemCalculateData]] = {}
        for cell in cells:
            cells_by_nmid.setdefault(cell.nmid, []).append(cell)

        for nmid, nmid_cells in cells_by_nmid.items():
            raw_profiles: dict[str, list[BidPosition]] | None = raw_profiles_by_nmid.get(nmid)
            if raw_profiles is None:
                continue
            contexts = build_keyword_v3_contexts(keywords, raw_profiles)
            ladder_inputs = LadderInputs.from_contexts(
                contexts,
                campaign_orders_per_cart_7d=campaign_opc,
            )
            ctx_by_ks_id = {
                ctx.keyword.keyword_setting_original_id: ctx for ctx in contexts
            }
            for cell in nmid_cells:
                if cell.strategy_mode is None:
                    continue
                ctx = ctx_by_ks_id.get(cell.keyword_setting_original_id)
                if ctx is None:
                    continue
                cap_bid = _matrix_cap_for_ctx(ctx, ladder_inputs, cell.strategy_mode)
                if cap_bid is not None:
                    cap_index[(cell.search_adv_id, cell.nmid, cell.cluster)] = cap_bid

    return cap_index


def apply_v3_cluster_bid_safety_cap(
    *,
    command: UpdateBidsCommand,
    map_datas: set[AdvIdItemCalculateData],
    calculation_inputs: list[CalculationInput],
    fact_datas: dict[int, FactData],
    plan_datas: dict[int, PlanData],
    cap_index: dict[CellKey, int],
    stored_bids: dict[ClusterBidKey, int],
    keywords_by_cell: dict[CellKey, CalculatedKeyword],
) -> UpdateBidsCommand:
    """Post-pass: clamp / inject ``NewBid`` до матричного cap при overspend по Auto adv_id."""
    calc_by_key: dict[CellKey, CalculationInput] = {
        (ci.search_adv_id, ci.nmid, ci.cluster): ci for ci in calculation_inputs
    }
    outgoing_by_key: dict[CellKey, NewBid] = {
        (nb.search_adv_id, nb.nmid, nb.cluster): nb for nb in command.new_bids
    }
    trace_defaults = trace_target_defaults()
    trace_shop_id = trace_defaults.get("shop_id")

    for cell in map_datas:
        if not cell.v3_managed:
            continue
        cell_key: tuple[int, int, str]= (cell.search_adv_id, cell.nmid, cell.cluster)
        trace_cell = (
            is_trace_enabled()
            and is_trace_cell(
                shop_id=trace_shop_id,
                adv_id=cell.adv_id,
                search_adv_id=cell.search_adv_id,
                nmid=cell.nmid,
                ks_id=cell.keyword_setting_original_id,
                key=cell.cluster,
            )
        )
        skip = _overspend_reason(cell.adv_id, fact_datas, plan_datas)
        if skip is not None:
            if trace_cell:
                log_cluster_bid_trace(
                    step="safety_cap",
                    adv_id=cell.adv_id,
                    search_adv_id=cell.search_adv_id,
                    nmid=cell.nmid,
                    ks_id=cell.keyword_setting_original_id,
                    key=cell.cluster,
                    action="skip",
                    skip_reason=skip,
                )
            continue

        cap_bid = cap_index.get(cell_key)
        if cap_bid is None:
            if trace_cell:
                log_cluster_bid_trace(
                    step="safety_cap",
                    adv_id=cell.adv_id,
                    search_adv_id=cell.search_adv_id,
                    nmid=cell.nmid,
                    ks_id=cell.keyword_setting_original_id,
                    key=cell.cluster,
                    action="skip",
                    skip_reason="no_cap_bid",
                )
            continue

        calc_input = calc_by_key.get(cell_key)
        keyword = keywords_by_cell.get(cell_key)
        reference_bid = resolve_reference_bid_for_cap(
            search_adv_id=cell.search_adv_id,
            nmid=cell.nmid,
            cluster=cell.cluster,
            stored_bids=stored_bids,
            keyword=keyword,
            calculation_input=calc_input,
        )
        if reference_bid is None:
            if trace_cell:
                log_cluster_bid_trace(
                    step="safety_cap",
                    adv_id=cell.adv_id,
                    search_adv_id=cell.search_adv_id,
                    nmid=cell.nmid,
                    ks_id=cell.keyword_setting_original_id,
                    key=cell.cluster,
                    action="skip",
                    skip_reason="no_reference_bid",
                )
            continue

        existing = outgoing_by_key.get(cell_key)
        candidate_bid = existing.new_bid if existing is not None else None
        effective = candidate_bid if candidate_bid is not None else reference_bid
        if effective <= cap_bid:
            if trace_cell:
                log_cluster_bid_trace(
                    step="safety_cap",
                    adv_id=cell.adv_id,
                    search_adv_id=cell.search_adv_id,
                    nmid=cell.nmid,
                    ks_id=cell.keyword_setting_original_id,
                    key=cell.cluster,
                    action="pass",
                    skip_reason="already_under_cap",
                    candidate_bid=candidate_bid,
                    cap_bid=cap_bid,
                    reference_bid=reference_bid,
                    outgoing_bid=effective,
                )
            continue

        outgoing_bid = cap_bid

        fact = fact_datas[cell.adv_id]
        plan = plan_datas[cell.adv_id]
        strategy_mode = cell.strategy_mode
        current_state = strategy_mode.name if strategy_mode is not None else None

        if existing is not None:
            baseline_bid = existing.new_bid
            new_bid = NewBid(
                search_adv_id=existing.search_adv_id,
                nmid=existing.nmid,
                cluster=existing.cluster,
                new_bid=outgoing_bid,
                bidder_keyword_status=existing.bidder_keyword_status,
                step=existing.step,
                direct=_cap_direct_vs_baseline(
                    outgoing_bid=outgoing_bid,
                    baseline_bid=baseline_bid,
                ),
            )
        else:
            new_bid = NewBid(
                search_adv_id=cell.search_adv_id,
                nmid=cell.nmid,
                cluster=cell.cluster,
                new_bid=outgoing_bid,
                bidder_keyword_status=BidderKeywordStatus.GOOD,
                step=max(1, cell.step),
                direct=_cap_direct_vs_baseline(
                    outgoing_bid=outgoing_bid,
                    baseline_bid=reference_bid,
                ),
            )

        outgoing_by_key[cell_key] = new_bid
        if trace_cell:
            log_cluster_bid_trace(
                step="safety_cap",
                adv_id=cell.adv_id,
                search_adv_id=cell.search_adv_id,
                nmid=cell.nmid,
                ks_id=cell.keyword_setting_original_id,
                key=cell.cluster,
                action="clamp",
                candidate_bid=candidate_bid,
                cap_bid=cap_bid,
                reference_bid=reference_bid,
                outgoing_bid=outgoing_bid,
                fact_pay_for_order=fact.pay_for_order,
                max_pay_for_order=plan.max_pay_for_order,
                current_state=current_state,
            )
        logger.info(
            "v3_cluster_bid_safety_cap_applied",
            extra={
                "search_adv_id": cell.search_adv_id,
                "keyword_setting_original_id": cell.keyword_setting_original_id,
                "fact_pay_for_order": fact.pay_for_order,
                "max_pay_for_order": plan.max_pay_for_order,
                "current_state": current_state,
                "reference_bid": reference_bid,
                "candidate_bid": candidate_bid,
                "cap_bid": cap_bid,
                "outgoing_bid": outgoing_bid,
                "reason": "overspend_matrix_cap",
            },
        )

    return UpdateBidsCommand(new_bids=list(outgoing_by_key.values()))
