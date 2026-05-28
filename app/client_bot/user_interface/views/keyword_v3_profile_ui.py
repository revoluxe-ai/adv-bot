"""Форматирование профиля ключа V3 (лестница stage) для карточки Telegram.

Текст вставляется в ``KeywordSettingMessage`` с ``ParseMode.MARKDOWN`` (legacy V1):
экранируем только ``_``, ``*``, ``[``, ````` — не синтаксис MarkdownV2.
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
    """Срез профиля для одного ключа: кандидаты M/O/C и целевые позиции по режимам."""

    current_mode: KeywordStrategyMode
    candidates: dict[AggressionTargetMode, ModeCandidate]
    target_positions_by_mode: dict[KeywordStrategyMode, int | None]


def format_keyword_v3_profile_block(data: KeywordV3ProfileData | None) -> str:
    """Текст блока профиля; ``None`` — сообщение о недоступности данных."""
    if data is None:
        return _PROFILE_UNAVAILABLE

    lines = ["📊 *Профиль ключа (V3):*"]
    for mode in _LADDER_ORDER:
        lines.append(_format_stage_line(data, mode))
    return "\n".join(lines) + "\n"


def _format_stage_line(data: KeywordV3ProfileData, mode: KeywordStrategyMode) -> str:
    star = "🌟 " if data.current_mode == mode else "   "
    letter = strategy_mode_letter(mode)

    if mode == KeywordStrategyMode.OFF:
        return f"{star}{letter} OFF — отключен"

    agg = _MODE_TO_AGG.get(mode)
    assert agg is not None
    cand = data.candidates.get(agg)
    label = _escape_markdown_v1(mode.name)
    if cand is None or not cand.is_valid:
        reason = ""
        if cand is not None and cand.invalid_reason:
            raw = _INVALID_REASON_SHORT.get(
                cand.invalid_reason, cand.invalid_reason
            )
            reason = f" ({_escape_markdown_v1(raw)})"
        return f"{star}{letter} {label} — —{reason}"

    pos = int(cand.position) if cand.position is not None else "—"
    cpm = int(cand.bid + 0.5) if cand.bid is not None else "—"
    cpo = f"{cand.predicted_cpa:.2f}" if cand.predicted_cpa is not None else "—"
    target = data.target_positions_by_mode.get(mode)
    if target == 0:
        target_str = "0 (мин.)"
    elif target is not None:
        target_str = str(target)
    else:
        target_str = "—"
    return (
        f"{star}{letter} {label} — поз. {pos} | CPM {cpm} "
        f"| CPO {cpo} ₽ | цель {target_str}"
    )

