"""Форматирование профиля ключа V3 (лестница stage) для карточки Telegram.

``KeywordSettingMessage`` использует ``ParseMode.MARKDOWN`` (legacy V1). Курсив ``_…_``
здесь не применяем: клиент часто показывает ``\\_`` буквально. Заголовок — ``*bold*``;
остальной текст — plain, без ``_`` в разметке.

Отдельно: **РК 7д**, raw и **сглаженная** ключевая корз→заказ (prior к РК).
CPO на точке CH = ``к→к`` × сглаженный ``orders_per_cart`` (SSOT ``orders_per_cart_for_ctx``).

На V3-карточке — компактная строка последнего решающего executor на тике
(``V3KeywordChanges`` Redis, SSOT ``last_decisive_step``).

Admin debug: экран «Почему бот так решил?» — ``format_keyword_v3_decision_trace_screen``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from app.client_bot.user_interface.views.keyword_strategy_ui import strategy_mode_letter
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.executor_phase_map import (
    EXECUTOR_SHORT_LABEL,
    phase_id_for_executor,
    short_label_for_executor,
    title_ru_for_phase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.keyword_entry import (
    find_keyword_change_entry,
    last_decisive_step,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.models import (
    V3KeywordChangesSnapshot,
    V3KeywordStepRecord,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
        ShelfClickMode,
    )

_ACTION_RU: dict[str, str] = {
    "UP": "↑",
    "DOWN": "↓",
    "FORCE_OFF": "OFF",
}

_TARGET_PLACE_STEP_RE = re.compile(r"^(\d+) \((.+)\)$")
_MSK_TZ = timezone(timedelta(hours=3))
_TICK_TIME_FMT = "%H:%M:%S %d-%m-%Y"

_PROFILE_UNAVAILABLE = (
    "📊 *Профиль ключа (V3):* недоступен (нет данных CH/WB)\n"
)

# Telegram legacy Markdown: _, *, `, [ вне разметки
_MARKDOWN_V1_ESCAPE = re.compile(r"([_*`\[])")


def escape_markdown_v1(text: str) -> str:
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
    "no_rk_conv_carts_to_orders": "нет корз→заказ РК 7д",
    "optimum_score_non_positive": "optimum ≤ 0",
    "no_valid_ch_ladder": "нет валид. CH ladder",
    "no_ch_min_only": "нет CH профиля",
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
    conv_views_to_cart: float | None = None
    conv_views_to_orders: float | None = None
    v2_pay_for_order: float | None = None
    keyword_pay_for_order: float | None = None
    campaign_worst_only: bool = False
    campaign_worst_costs: dict[AggressionTargetMode, float] | None = None
    stage_sources: dict[AggressionTargetMode, str] | None = None
    campaign_orders_per_cart_7d: float | None = None
    key_orders_7d: int = 0
    key_carts_7d: int = 0
    key_orders_per_cart_raw: float | None = None
    key_orders_per_cart_smoothed: float | None = None
    prior_carts_strength: int = 0
    rec_orders_per_view: float | None = None
    shelf_click_mode: "ShelfClickMode | None" = None

    @property
    def rk_orders_per_cart(self) -> float | None:
        """Deprecated: ``campaign_orders_per_cart_7d`` (baseline РК для prior/UI)."""
        return self.campaign_orders_per_cart_7d


def _format_pct_compact(value: float | None, *, decimals: int = 2) -> str:
    """Доля → компактные проценты для Telegram (``0`` → ``0%``, ``0.07`` → ``0.07%``)."""
    if value is None:
        return "—"
    pct = value * 100
    if abs(pct) < 10 ** (-decimals):
        return "0%"
    text = f"{pct:.{decimals}f}".rstrip("0").rstrip(".")
    return f"{text}%"


def _stage_uses_campaign_max_rk(
    data: KeywordV3ProfileData, agg: AggressionTargetMode
) -> bool:
    """Deprecated: worst-imputation удалён; maxРК в UI не показываем."""
    _ = data, agg
    return False


def _worst_suffix_for_stage(
    data: KeywordV3ProfileData, agg: AggressionTargetMode
) -> str:
    """Deprecated: worst-imputation удалён."""
    _ = data, agg
    return ""


def _profile_shows_max_rk_legend(data: KeywordV3ProfileData) -> bool:
    """Deprecated: worst-imputation удалён."""
    _ = data
    return False


def _keyword_ladder_ui_suppressed(data: KeywordV3ProfileData) -> bool:
    """N-state / NO CH min-only: лестница M/O/C на ключе не показывается."""
    return data.n_state or data.no_ch_min_only


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


def _format_rk_cart_to_order_line(data: KeywordV3ProfileData) -> str:
    """Конверсия РК корзина→заказ (7д, ``wb_common_stat``) — prior для сглаживания ключа."""
    campaign = data.campaign_orders_per_cart_7d
    if campaign is None or campaign <= 0:
        return "   РК 7д корз→заказ: — (нет данных wb_common_stat)"
    carts_per_order = 1.0 / float(campaign)
    pct = _format_pct_compact(campaign)
    return (
        f"   РК 7д корз→заказ: {pct} "
        f"({campaign:.3g} зак/корз, {carts_per_order:.2g} корз/зак)"
    )


def _format_key_cart_to_order_lines(data: KeywordV3ProfileData) -> list[str]:
    """Raw и сглаженная корз→заказ ключа + prior."""
    orders = data.key_orders_7d
    carts = data.key_carts_7d
    raw_pct = _format_pct_compact(data.key_orders_per_cart_raw)
    smooth_pct = _format_pct_compact(data.key_orders_per_cart_smoothed)
    prior = data.prior_carts_strength
    return [
        f"   ключ корз→заказ raw: {orders} зак / {carts} корз = {raw_pct}",
        f"   ключ корз→заказ сглаж.: {smooth_pct}",
        f"   prior: {prior} корзин",
    ]


def _format_current_mode_target_line(data: KeywordV3ProfileData) -> str | None:
    """Позиция и ставка CH для текущего stored-режима (сверка с «Целевая позиция» в карточке)."""
    if data.current_mode == KeywordStrategyMode.OFF:
        return None
    agg = _MODE_TO_AGG.get(data.current_mode)
    if agg is None:
        return None
    cand = data.candidates.get(agg)
    if cand is None or not cand.is_valid:
        return None
    letter = strategy_mode_letter(data.current_mode)
    pos = int(cand.position) if cand.position is not None else "—"
    bid = int(cand.bid + 0.5) if cand.bid is not None else "—"
    return f"   Цель режима {letter}: п{pos}|с{bid} (из CH M/O/C)"


def _format_metrics_legend_lines(data: KeywordV3ProfileData) -> list[str]:
    """Легенда метрик строк M/O/C и формула CPO."""
    lines = [
        "   п|с|к→к|к→з|PFC|CPO — поз|ставка|conv CH|к→з|PFC|CPO заказа",
        "   CPO = PFC / (к→з) = к→к CH × сглаженная ключевая корз→заказ (prior к РК 7д)",
        "   П — state выше полочной конверсии по прогнозу к→з",
        "   Н — конверсия state неизвестна (условно полочный); UP разрешён",
    ]
    if _profile_shows_max_rk_legend(data):
        lines.append("   maxРК — max CPO режима по ключам РК с CH (worst)")
    return lines


def _format_diagnostic_line(
    diagnostic: KeywordV3DataDiagnostic,
    *,
    no_ch_min_only: bool = False,
) -> str:
    """Строка «что есть / чего нет» для V2 CPO / себест. заказа и CH-матрицы."""
    ch = "✓" if diagnostic.has_ch_position_profile else "✗"
    if no_ch_min_only:
        pfo = "✓" if diagnostic.has_v2_cpo else "✗"
        line = f"   Данные: себест. заказа {pfo} | CH матрица {ch}"
    else:
        v2 = "✓" if diagnostic.has_v2_cpo else "✗"
        line = f"   Данные: V2 CPO {v2} | CH матрица {ch}"
    missing = diagnostic.missing_labels_ru()
    if missing:
        gaps = "; ".join(missing)
        line += f"\n   Нет: {gaps}"
    return line


def _format_tick_at_msk(tick_at: datetime) -> str:
    """Время тика V3 в MSK для компактной строки executor."""
    dt = tick_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_MSK_TZ).strftime(_TICK_TIME_FMT)


def _executor_name_from_short_label(short_label: str) -> str:
    """Обратный lookup short label → имя executor (fallback — исходная метка)."""
    for executor_name, label in EXECUTOR_SHORT_LABEL.items():
        if label == short_label:
            return executor_name
    return short_label


def format_decisive_step_body(
    decisive: V3KeywordStepRecord | str,
) -> tuple[str, str, str] | None:
    """Короткая метка, title_ru и тело строки для решающего шага."""
    if isinstance(decisive, V3KeywordStepRecord):
        short = short_label_for_executor(decisive.executor_name)
        title = title_ru_for_phase(phase_id_for_executor(decisive.executor_name))
        action_ru = _ACTION_RU.get(decisive.action, decisive.action)
        body = f"{action_ru} {decisive.from_mode}→{decisive.to_mode}"
        return short, title, body

    match = _TARGET_PLACE_STEP_RE.match(decisive)
    if match is None:
        return None
    place, short = match.group(1), match.group(2)
    executor_name = _executor_name_from_short_label(short)
    title = title_ru_for_phase(phase_id_for_executor(executor_name))
    return short, title, f"tp → {place}"


def format_keyword_v3_last_tick_executor_line(
    *,
    keyword_setting_id: int,
    keyword_changes: V3KeywordChangesSnapshot | None,
) -> str:
    """Компактная строка последнего решающего executor ключа на V3-тике.

    Args:
        keyword_setting_id: ID ``KeywordSetting``.
        keyword_changes: Audit последнего тика из Redis; ``None`` — нет данных.

    Returns:
        ``"V3 · …\\n"`` или пустая строка, если ключ не менялся / нет решающего шага.
    """
    if keyword_changes is None:
        return ""
    entry = find_keyword_change_entry(keyword_changes, keyword_setting_id)
    if entry is None:
        return ""
    decisive = last_decisive_step(entry)
    if decisive is None:
        return ""
    parts = format_decisive_step_body(decisive)
    if parts is None:
        return ""
    short, title, body = parts
    time_str = _format_tick_at_msk(keyword_changes.tick_at)
    return f"V3 · {short} · {title}: {body} · {time_str}\n"


NON_V3_DECISION_TRACE_MESSAGE = (
    "Разбор решений доступен только для V3-управления."
)

_NO_CHANGING_EXECUTOR_NOTE = (
    "В последнем сохранённом V3-тике по этому ключу нет изменяющего "
    "executor'а. Полный каскад SKIP/APPLY будет добавлен отдельным "
    "trace-модулем."
)

REASON_NOT_IN_JOURNAL = (
    "Причина не зафиксирована в текущем журнале решений."
)

DECISION_ACTION_LABEL: dict[str, str] = {
    "UP": "UP",
    "DOWN": "DOWN",
    "FORCE_OFF": "FORCE_OFF",
    "NOOP": "DO_NOTHING",
    "TARGET_PLACE": "TARGET_PLACE",
}


def keyword_v3_decision_trace_button_label(display_status: KeywordStatus) -> str:
    """Текст admin-кнопки разбора решения V3 в карточке ключа."""
    if display_status == KeywordStatus.GOOD:
        return "🔎 Почему бот включил?"
    return "🔎 Почему бот не включил?"


def format_keyword_v3_decision_trace_screen(
    *,
    nmid: str,
    keyword_text: str,
    display_status: KeywordStatus,
    keyword_setting_id: int,
    keyword_changes: V3KeywordChangesSnapshot | None,
) -> str:
    """Текст экрана «Почему бот так решил?» (legacy adapter → ViewData formatter).

    Args:
        nmid: Артикул(ы) кампании для заголовка.
        keyword_text: Текст ключевого запроса.
        display_status: Статус ключа для UI (good/bad/pause).
        keyword_setting_id: ID ``KeywordSetting``.
        keyword_changes: Audit последнего V3-тика из Redis (legacy).

    Returns:
        Markdown-текст для ``ParseMode.MARKDOWN`` (legacy V1).
    """
    from app.client_bot.user_interface.services.keyword_decision_trace_loader import (
        KeywordDecisionTraceViewData,
        ProcessingOutcome,
        TracePresence,
    )
    from app.client_bot.user_interface.views.keyword_decision_trace_ui import (
        format_keyword_decision_trace_screen as _format_from_view,
    )

    legacy_decisive = None
    legacy_tick_at = None
    source: str = "empty"
    if keyword_changes is not None:
        entry = find_keyword_change_entry(keyword_changes, keyword_setting_id)
        if entry is not None:
            legacy_decisive = last_decisive_step(entry)
            if legacy_decisive is not None:
                source = "legacy_changes"
                legacy_tick_at = keyword_changes.tick_at

    view = KeywordDecisionTraceViewData(
        nmid_display=nmid,
        keyword_text=keyword_text,
        display_status=display_status,
        bot_active=True,
        keyword_setting_id=keyword_setting_id,
        trace_presence=TracePresence.NO_SNAPSHOT,
        processing_outcome=ProcessingOutcome.UNKNOWN,
        tick_started_at=None,
        processing_started_at=None,
        tick_finished_at=None,
        entry=None,
        source=source,  # type: ignore[arg-type]
        legacy_decisive=legacy_decisive,
        legacy_tick_at=legacy_tick_at,
    )
    return _format_from_view(view)


def format_keyword_v3_profile_block(data: KeywordV3ProfileData | None) -> str:
    """Текст блока профиля; ``None`` — legacy «недоступен» без детализации."""
    if data is None:
        return _PROFILE_UNAVAILABLE

    if data.load_failure:
        reason = escape_markdown_v1(data.load_failure)
        return f"📊 *Профиль ключа (V3):* недоступен — {reason}\n"

    header = "📊 *Профиль ключа (V3):*"
    if data.n_state:
        header = "📊 *Профиль ключа (V3):* N-state"
    elif data.no_ch_min_only:
        header = "📊 *Профиль ключа (V3):* NO CH (только MIN)"
    elif data.campaign_worst_only:
        header = "📊 *Профиль ключа (V3):* max CPO по РК (нет CH на ключе)"
    elif data.diagnostic is not None and data.diagnostic.has_ch_position_profile:
        if data.diagnostic.decision_tier == KeywordV3DecisionTier.NO_CONV:
            header = "📊 *Профиль ключа (V3):* CH (нет своей conv)"
        # FULL и прочие — обычный заголовок без «импутации»
    lines = [header]
    if data.diagnostic is not None:
        lines.append(
            _format_diagnostic_line(
                data.diagnostic, no_ch_min_only=data.no_ch_min_only
            )
        )
    if not data.no_ch_min_only:
        lines.append(_format_rk_cart_to_order_line(data))
        lines.extend(_format_key_cart_to_order_lines(data))
    target_line = _format_current_mode_target_line(data)
    if target_line is not None:
        lines.append(target_line)
    if not _keyword_ladder_ui_suppressed(data):
        if _ladder_has_valid_candidate(data):
            if data.campaign_worst_only:
                lines.append("   CPO — max state_cost M/O/C по ключам РК с CH")
            else:
                lines.extend(_format_metrics_legend_lines(data))
        for mode in _LADDER_ORDER:
            lines.append(_format_stage_line(data, mode))
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
    pfo_source = (data.stage_sources or {}).get(agg) == "pay_for_order"
    if cand is not None and cand.is_valid and cand.predicted_cpa is not None:
        cpo = f"{cand.predicted_cpa:.2f}"
        if pfo_source and mode == KeywordStrategyMode.MIN_CPA:
            pfo_label = (
                f"{data.keyword_pay_for_order:.2f}"
                if data.keyword_pay_for_order is not None
                else cpo
            )
            return f"{star}{letter} п0|min|CPO{pfo_label}|pay_for_order"
        if cand.position is None or cand.bid is None:
            worst_suffix = _worst_suffix_for_stage(data, agg)
            if worst_suffix:
                return f"{star}{letter} CPO={cpo}{worst_suffix}"
            if _stage_uses_campaign_max_rk(data, agg):
                return f"{star}{letter} CPO={cpo} (max РК)"
            return f"{star}{letter} CPO={cpo}"
    if cand is None or not cand.is_valid:
        reason = ""
        if cand is not None and cand.invalid_reason:
            raw = _INVALID_REASON_SHORT.get(
                cand.invalid_reason, cand.invalid_reason
            )
            reason = f" ({escape_markdown_v1(raw)})"
        return f"{star}{letter} — —{reason}"

    pos = int(cand.position) if cand.position is not None else "—"
    bid = int(cand.bid + 0.5) if cand.bid is not None else "—"
    cpo = f"{cand.predicted_cpa:.2f}" if cand.predicted_cpa is not None else "—"
    pfc = (
        f"{cand.pay_for_cart:.0f}"
        if cand.pay_for_cart is not None
        else "—"
    )
    conv_cart = _format_pct_compact(cand.predicted_conversion)
    conv_order = _format_pct_compact(cand.predicted_orders_per_view)
    mark = _rec_gate_mark_for_stage(data, cand)
    mark_prefix = f"{mark} " if mark else ""
    worst_suffix = _worst_suffix_for_stage(data, agg)
    metrics = f"п{pos}|с{bid}|к→к{conv_cart}|к→з{conv_order}|PFC{pfc}|CPO{cpo}"
    if worst_suffix:
        return f"{star}{mark_prefix}{letter} {metrics}{worst_suffix}"
    return f"{star}{mark_prefix}{letter} {metrics}"


def _rec_gate_mark_for_stage(
    data: KeywordV3ProfileData,
    cand: ModeCandidate,
) -> str:
    """Марка полочного gate: ``П`` / ``Н`` / пусто."""
    if data.shelf_click_mode is None:
        return ""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
        V3RolloutAggressiveness,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        SelectionPolicy,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate import (
        resolve_rec_gate_mark,
    )

    policy = SelectionPolicy.from_aggressiveness(
        click_mode=data.shelf_click_mode,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    return resolve_rec_gate_mark(
        cand,
        policy=policy,
        rec_orders_per_view=data.rec_orders_per_view,
        orders_per_cart=data.key_orders_per_cart_smoothed,
    )

