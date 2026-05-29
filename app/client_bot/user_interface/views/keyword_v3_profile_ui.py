"""Форматирование профиля ключа V3 (лестница stage) для карточки Telegram.

``KeywordSettingMessage`` использует ``ParseMode.MARKDOWN`` (legacy V1). Курсив ``_…_``
здесь не применяем: клиент часто показывает ``\\_`` буквально. Заголовок — ``*bold*``;
остальной текст — plain, без ``_`` в разметке.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.client_bot.user_interface.views.keyword_strategy_ui import strategy_mode_letter
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    KeywordV3DecisionTier,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    KeywordV3DataDiagnostic,
)

_PROFILE_UNAVAILABLE = (
    "📊 *Профиль ключа (V3):* недоступен (нет данных CH/WB)\n"
)

# Telegram legacy Markdown: _, *, `, [ вне разметки
_MARKDOWN_V1_ESCAPE = re.compile(r"([_*`\[])")


def _escape_markdown_v1(text: str) -> str:
    """Экранирование для ``ParseMode.MARKDOWN`` (не MarkdownV2)."""
    return _MARKDOWN_V1_ESCAPE.sub(r"\\\1", text)

_LADDER_ORDER: tuple[KeywordStrategyMode, ...] = (
    KeywordStrategyMode.OFF,
    KeywordStrategyMode.MIN_CPA,
    KeywordStrategyMode.OPTIMUM,
    KeywordStrategyMode.MAX_CONVERSION,
)

_MODE_TO_AGG: dict[KeywordStrategyMode, AggressionTargetMode | None] = {
    KeywordStrategyMode.OFF: None,
    KeywordStrategyMode.MIN_CPA: AggressionTargetMode.MIN_CPA,
    KeywordStrategyMode.OPTIMUM: AggressionTargetMode.OPTIMUM,
    KeywordStrategyMode.MAX_CONVERSION: AggressionTargetMode.MAX_CONVERSION,
}

_INVALID_REASON_SHORT: dict[str, str] = {
    "no_position_profile": "нет профиля",
    "no_conversion_points": "нет конверсий",
    "no_keyword_conv_views_to_orders": "нет conv показ→заказ",
    "optimum_score_non_positive": "optimum ≤ 0",
}


@dataclass(frozen=True, slots=True)
class KeywordV3ProfileData:
    """Срез профиля для одного ключа: кандидаты M/O/C, N-state или тех. сбой загрузки."""

    current_mode: KeywordStrategyMode
    candidates: dict[AggressionTargetMode, ModeCandidate]
    n_state: bool = False
    no_ch_min_only: bool = False
    diagnostic: KeywordV3DataDiagnostic | None = None
    load_failure: str | None = None
    keyword_ctr: float | None = None
    conv_views_to_orders: float | None = None
    v2_pay_for_order: float | None = None
    campaign_worst_only: bool = False
    campaign_worst_costs: dict[AggressionTargetMode, float] | None = None
    stage_sources: dict[AggressionTargetMode, str] | None = None


def _format_pct_compact(value: float | None, *, decimals: int = 2) -> str:
    """Доля → компактные проценты для Telegram (``0`` → ``0%``, ``0.07`` → ``0.07%``)."""
    if value is None:
        return "—"
    pct = value * 100
    if abs(pct) < 10 ** (-decimals):
        return "0%"
    text = f"{pct:.{decimals}f}".rstrip("0").rstrip(".")
    return f"{text}%"


def _ladder_has_valid_candidate(data: KeywordV3ProfileData) -> bool:
    """Есть хотя бы одна валидная строка M/O/C — показываем легенду метрик."""
    for mode in (
        KeywordStrategyMode.MIN_CPA,
        KeywordStrategyMode.OPTIMUM,
        KeywordStrategyMode.MAX_CONVERSION,
    ):
        agg = _MODE_TO_AGG.get(mode)
        if agg is None:
            continue
        cand = data.candidates.get(agg)
        if cand is not None and cand.is_valid:
            return True
    return False


def _format_metrics_legend_lines(data: KeywordV3ProfileData) -> list[str]:
    """Легенда: сокращения строк M/O/C и общая к→з ключа."""
    conv_order = _format_pct_compact(data.conv_views_to_orders)
    lines = [
        "   п|с|CTR|CPO — поз|ставка|факт|state_cost",
        f"   к→з {conv_order} — conv ключа (своя)",
    ]
    if data.diagnostic is not None and data.diagnostic.imputed_conv:
        lines.append("   maxРК — max CPO режима по ключам РК с CH (worst)")
    return lines


def _format_diagnostic_line(diagnostic: KeywordV3DataDiagnostic) -> str:
    """Строка «что есть / чего нет» для V2 CPO и CH-матрицы (plain text)."""
    v2 = "✓" if diagnostic.has_v2_cpo else "✗"
    ch = "✓" if diagnostic.has_ch_position_profile else "✗"
    line = f"   Данные: V2 CPO {v2} | CH матрица {ch}"
    missing = diagnostic.missing_labels_ru()
    if missing:
        gaps = "; ".join(missing)
        line += f"\n   Нет: {gaps}"
    return line


def format_keyword_v3_profile_block(data: KeywordV3ProfileData | None) -> str:
    """Текст блока профиля; ``None`` — legacy «недоступен» без детализации."""
    if data is None:
        return _PROFILE_UNAVAILABLE

    if data.load_failure:
        reason = _escape_markdown_v1(data.load_failure)
        return f"📊 *Профиль ключа (V3):* недоступен — {reason}\n"

    header = "📊 *Профиль ключа (V3):*"
    if data.n_state:
        header = "📊 *Профиль ключа (V3):* N-state"
    elif data.no_ch_min_only:
        header = "📊 *Профиль ключа (V3):* NO CH (только MIN)"
    elif data.campaign_worst_only:
        header = "📊 *Профиль ключа (V3):* max CPO по РК (нет CH на ключе)"
    elif data.diagnostic is not None and data.diagnostic.has_ch_position_profile:
        if data.diagnostic.imputed_conv:
            if data.diagnostic.decision_tier == KeywordV3DecisionTier.RK_AGGREGATE:
                header = "📊 *Профиль ключа (V3):* CH + имп. conv (РК)"
            elif data.diagnostic.decision_tier == KeywordV3DecisionTier.PEER_MAX:
                header = "📊 *Профиль ключа (V3):* CH + имп. conv (max ключ)"
            else:
                header = "📊 *Профиль ключа (V3):* CH + имп. conv"
        elif data.diagnostic.decision_tier == KeywordV3DecisionTier.NO_CONV:
            header = "📊 *Профиль ключа (V3):* CH + max CPO по РК (нет conv)"
        # FULL и прочие — обычный заголовок без «импутации»
    lines = [header]
    if data.diagnostic is not None:
        lines.append(_format_diagnostic_line(data.diagnostic))
    if _ladder_has_valid_candidate(data):
        if data.campaign_worst_only:
            lines.append("   CPO — max state_cost M/O/C по ключам РК с CH")
        else:
            lines.extend(_format_metrics_legend_lines(data))
    for mode in _LADDER_ORDER:
        lines.append(_format_stage_line(data, mode))
    if data.n_state:
        lines.append(
            "   M + target 0 → min bid WB, белый список (N-state bootstrap)"
        )
    elif data.no_ch_min_only:
        lines.append(
            "   M + target 0 → min bid WB, белый список (NO CH bootstrap)"
        )
    return "\n".join(lines) + "\n"


def _format_stage_line(data: KeywordV3ProfileData, mode: KeywordStrategyMode) -> str:
    """Одна строка ступени лестницы с метриками профиля."""
    star = "🌟 " if data.current_mode == mode else "   "
    letter = strategy_mode_letter(mode)

    if mode == KeywordStrategyMode.OFF:
        return f"{star}{letter} OFF — отключен"

    agg = _MODE_TO_AGG.get(mode)
    assert agg is not None
    cand = data.candidates.get(agg)
    if cand is not None and cand.is_valid and cand.predicted_cpa is not None:
        cpo = f"{cand.predicted_cpa:.2f}"
        if cand.position is None or cand.bid is None:
            suffix = " (max РК)" if data.campaign_worst_only else ""
            return f"{star}{letter} CPO={cpo}{suffix}"
    if cand is None or not cand.is_valid:
        if mode == KeywordStrategyMode.MIN_CPA and data.no_ch_min_only:
            cpo = (
                f"{data.v2_pay_for_order:.2f}"
                if data.v2_pay_for_order is not None
                else "—"
            )
            return f"{star}{letter} CPO={cpo} (V2) | target 0 — min bid WB"
        reason = ""
        if cand is not None and cand.invalid_reason:
            raw = _INVALID_REASON_SHORT.get(
                cand.invalid_reason, cand.invalid_reason
            )
            reason = f" ({_escape_markdown_v1(raw)})"
        return f"{star}{letter} — —{reason}"

    pos = int(cand.position) if cand.position is not None else "—"
    bid = int(cand.bid + 0.5) if cand.bid is not None else "—"
    cpo = f"{cand.predicted_cpa:.2f}" if cand.predicted_cpa is not None else "—"
    ctr = _format_pct_compact(data.keyword_ctr)
    worst_suffix = ""
    if data.campaign_worst_costs is not None:
        worst_val = data.campaign_worst_costs.get(agg)
        if worst_val is not None:
            worst_suffix = f"|maxРК{worst_val:.0f}"
    src = (data.stage_sources or {}).get(agg, "")
    if src == "worst":
        cost_note = "maxРК"
    elif src == "profile" and worst_suffix:
        cost_note = "проф"
    else:
        cost_note = ""
    if cost_note and worst_suffix:
        return f"{star}{letter} п{pos}|с{bid}|CTR{ctr}|CPO{cpo}({cost_note}){worst_suffix}"
    if worst_suffix:
        return f"{star}{letter} п{pos}|с{bid}|CTR{ctr}|CPO{cpo}{worst_suffix}"
    return f"{star}{letter} п{pos}|с{bid}|CTR{ctr}|CPO{cpo}"

