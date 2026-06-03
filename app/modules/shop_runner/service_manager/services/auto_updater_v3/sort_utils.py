"""Сортировка ключей V3: shop-runner (MIN_CPO) и Telegram UI (профиль CH или pay_for_order)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    resolve_no_ch_operational_pay_for_order_cost,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    min_cpa_operational_via_pay_for_order,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
    state_candidates_by_mode_for_ctx,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordV3Eligibility,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

_HARD_STATUS_WHITE_LIST = 2


def pay_for_order_sort_key(kw: CalculatedKeyword) -> tuple[float, int]:
    """Ключ сортировки: дешёвые сверху; ``None`` pay_for_order — в конец."""
    pfo = kw.pay_for_order
    pay = float("inf") if pfo is None else float(pfo)
    ks_id = int(kw.keyword_setting_original_id or 0)
    return (pay, ks_id)


def sort_white_list_by_min_cpo(
    keywords: list[CalculatedKeyword],
) -> list[CalculatedKeyword]:
    """Белый список (``hard_status == 2``), сортировка по возрастанию ``pay_for_order``."""
    wl = [kw for kw in keywords if int(kw.hard_status) == _HARD_STATUS_WHITE_LIST]
    return sorted(wl, key=pay_for_order_sort_key)


def resolve_v3_ui_sort_mode(keyword: CalculatedKeyword) -> KeywordStrategyMode:
    """Режим для метрики сортировки UI: ``OFF`` → ``MIN_CPA``, иначе текущий ``strategy_mode``."""
    mode = keyword.strategy_mode
    if mode == KeywordStrategyMode.OFF:
        return KeywordStrategyMode.MIN_CPA
    return mode


def resolve_v3_ui_sort_cost(
    ctx: KeywordV3Context,
    ladder_inputs: LadderInputs,
    eligibility: KeywordV3Eligibility | None,
) -> float | None:
    """Метрика сортировки UI: свой ``state_cost`` из CH-профиля или NO DATA → ``pay_for_order``.

    Worst-импутация по РК **не** используется (выпилена из prod-контракта сортировки):
    нет валидной точки M/O/C на ключе → операционный ``pay_for_order``, иначе хвост по алфавиту.

    Args:
        ctx: Контекст ключа с ``position_profile``.
        ladder_inputs: Предрасчёт лестницы на РК (peer/eligibility).
        eligibility: Tier для NO CH / collapsed CH (MIN через PFO).

    Returns:
        Конечная метрика сортировки или ``None`` (хвост списка по алфавиту).
    """
    sort_mode = resolve_v3_ui_sort_mode(ctx.keyword)
    target = AggressionTargetMode[sort_mode.name]
    catalog = state_candidates_by_mode_for_ctx(ctx, ladder_inputs)

    if eligibility is not None and min_cpa_operational_via_pay_for_order(
        ctx, eligibility, catalog
    ):
        if sort_mode == KeywordStrategyMode.MIN_CPA:
            pfo = resolve_no_ch_operational_pay_for_order_cost(ctx.keyword)
            if pfo is not None:
                return float(pfo)
        pfo = resolve_no_ch_operational_pay_for_order_cost(ctx.keyword)
        return float(pfo) if pfo is not None else None

    mc = catalog.get(target)
    if mc is not None and mc.is_valid and mc.predicted_cpa is not None:
        return float(mc.predicted_cpa)

    pfo = resolve_no_ch_operational_pay_for_order_cost(ctx.keyword)
    if pfo is not None:
        return float(pfo)
    return None


def v3_ui_sort_key(
    keyword: CalculatedKeyword,
    *,
    ctx_by_ks_id: dict[int, KeywordV3Context],
    ladder_inputs: LadderInputs,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility],
) -> tuple[int, float, str]:
    """Ключ сортировки UI: bucket 0 — по cost asc, bucket 1 — алфавит в конце.

    Returns:
        ``(bucket, cost, text_lower)`` — ``bucket`` 0 при наличии метрики, иначе 1.
    """
    text_key = (keyword.text or "").casefold()
    ks_id = keyword.keyword_setting_original_id
    if ks_id is None:
        return (1, float("inf"), text_key)
    ctx = ctx_by_ks_id.get(int(ks_id))
    if ctx is None:
        return (1, float("inf"), text_key)
    elig = eligibility_by_ks_id.get(int(ks_id))
    cost = resolve_v3_ui_sort_cost(ctx, ladder_inputs, elig)
    if cost is None:
        return (1, float("inf"), text_key)
    return (0, cost, text_key)


def sort_keywords_by_current_state_cost(
    keywords: list[CalculatedKeyword],
    contexts: list[KeywordV3Context],
    ladder_inputs: LadderInputs,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility],
) -> list[CalculatedKeyword]:
    """Список ключей UI V3: asc по CH ``state_cost`` или ``pay_for_order`` (NO DATA), хвост — алфавит.

    Args:
        keywords: Отображаемые ключи (уже отфильтрованы в UI).
        contexts: Контексты с CH-профилями для тех же ключей.
        ladder_inputs: ``LadderInputs`` на РК.
        eligibility_by_ks_id: Карта eligibility по ``keyword_setting_id``.

    Returns:
        Новый отсортированный список (исходный не мутируется).
    """
    ctx_by_ks_id: dict[int, KeywordV3Context] = {}
    for ctx in contexts:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is not None:
            ctx_by_ks_id[int(ks_id)] = ctx

    return sorted(
        keywords,
        key=lambda kw: v3_ui_sort_key(
            kw,
            ctx_by_ks_id=ctx_by_ks_id,
            ladder_inputs=ladder_inputs,
            eligibility_by_ks_id=eligibility_by_ks_id,
        ),
    )
