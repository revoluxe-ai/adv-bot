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
    diagnostic: KeywordV3DataDiagnostic | None = None
    load_failure: str | None = None


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
    lines = [header]
    if data.diagnostic is not None:
        lines.append(_format_diagnostic_line(data.diagnostic))
    for mode in _LADDER_ORDER:
        lines.append(_format_stage_line(data, mode))
    if data.n_state:
        lines.append(
            "   M + target 0 → min bid WB, белый список (апдейтер)"
        )
    return "\n".join(lines) + "\n"


def _format_stage_line(data: KeywordV3ProfileData, mode: KeywordStrategyMode) -> str:
    star = "🌟 " if data.current_mode == mode else "   "
    letter = strategy_mode_letter(mode)

    if mode == KeywordStrategyMode.OFF:
        return f"{star}{letter} OFF — отключен"

    agg = _MODE_TO_AGG.get(mode)
    assert agg is not None
    cand = data.candidates.get(agg)
    if cand is None or not cand.is_valid:
        reason = ""
        if cand is not None and cand.invalid_reason:
            raw = _INVALID_REASON_SHORT.get(
                cand.invalid_reason, cand.invalid_reason
            )
            reason = f" ({_escape_markdown_v1(raw)})"
        return f"{star}{letter} — —{reason}"

    pos = int(cand.position) if cand.position is not None else "—"
    cpm = int(cand.bid + 0.5) if cand.bid is not None else "—"
    cpo = f"{cand.predicted_cpa:.2f}" if cand.predicted_cpa is not None else "—"
    return (
        f"{star}{letter} — поз. {pos} | CPM {cpm} | CPO {cpo} ₽"
    )

