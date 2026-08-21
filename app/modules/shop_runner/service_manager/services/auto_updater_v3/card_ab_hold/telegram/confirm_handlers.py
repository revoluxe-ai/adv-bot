"""Telegram handlers confirm-flow A/B Hold (ux contract §§5–10, §24).

Spec requirements:
- «Confirmation screens paginate keyword lists at a fixed page size»
- «Back preserves the confirmation draft; Cancel is a separate explicit action»
- stale callback → fail-closed redraw (§10)

WB-мутации не выполняются в handlers — sync owned by shop-runner.

Callback ACK: ``ImmediateCallbackAnswerUpdateMiddleware`` уже отвечает на
CallbackQuery; handlers не вызывают ``query.answer()`` — user-visible
пояснения через ``_notify_callback_user`` (message.answer / bot.send_message).
"""

from __future__ import annotations

import inspect
import logging
import math
from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias, cast

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.client_bot.user_interface.helpers.wb_user_cabinet import (
    get_wb_user_cabinet_for_adv_and_telegram,
)
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    CardAbHoldSyncStatus,
    DEFAULT_WARMUP_HOURS,
    normalize_card_ab_hold_sync_status,
    propose_target_places_from_positions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write import (
    EpochWriteError,
    clear_epoch_on_exit_in_session,
    confirm_auto_bid,
    confirm_auto_participation,
    confirm_keyword_set_and_start_warmup,
    confirm_target_places,
    set_warmup_duration,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.minus_freeze import (
    empty_allowed_snapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
    normalize_card_ab_hold_mode,
    normalize_card_ab_hold_phase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_decision import (
    AB_HOLD_S1_SOURCE_KEYWORDS_ATTR,
    eligible_keyword_texts_for_confirm,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.redis_coordination import (
    CardAbHoldSetupBlockRedisCache,
    CardAbHoldSignalRedisCache,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.actor import (
    MISSING_ACTOR_NOTICE,
    callback_actor_id as _callback_actor_id,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_callbacks import (
    CahAutoBidConfirm,
    CahAutoBidEdit,
    CahAutoParticipationConfirm,
    CahCancelConfirmNo,
    CahCancelConfirmYes,
    CahCancelOpen,
    CahConfirmBack,
    CahConfirmDisable,
    CahContinueToAuto,
    CahKeywordEditOpen,
    CahKeywordSetConfirm,
    CahKeywordToggle,
    CahOpenCurrentStep,
    CahPageNav,
    CahSyncStatusRefresh,
    CahTpConfirmAll,
    CahWarmupDurationConfirm,
    CahWarmupDurationPreset,
    CahWarmupStatusRefresh,
    ConfirmStep,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_draft import (
    bump_revision,
    clear_summary,
    close_cancel_dialog,
    discard_edit_draft_only,
    get_revision,
    is_stale_generation,
    is_stale_revision,
    should_show_w3_confirmed_read_only,
    load_draft,
    mark_summary_visible,
    open_cancel_dialog,
    reset_draft,
    save_draft,
    selected_keywords,
    set_page,
    set_w3_confirmed_visible,
    toggle_keyword_inclusion,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_keyboards import (
    build_a1_keyboard,
    build_a2_keyboard,
    build_cancel_dialog_keyboard,
    build_h1_keyboard,
    build_p1_keyboard,
    build_p2_keyboard,
    build_s1_keyboard,
    build_s2_keyboard,
    build_s3_keyboard,
    build_summary_keyboard,
    build_w3_confirmed_keyboard,
    build_w3_propose_keyboard,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_pagination import (
    paginate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_screens import (
    STALE_TOAST,
    build_a1_text,
    build_a2_text,
    build_cancel_dialog_text,
    build_h1_text,
    build_p1_text,
    build_p2_text,
    build_s1_text,
    build_s2_text,
    build_s3_text,
    build_summary_text,
    build_w3_confirmed_text,
    build_w3_propose_text,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.ui_access import (
    is_card_ab_hold_ui_visible,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

card_ab_hold_confirm_router = Router(name="card_ab_hold_confirm")

_GENERATION_PHASES = frozenset(
    {
        CardAbHoldPhase.PENDING_INTENT,
        CardAbHoldPhase.WB_SYNC,
        CardAbHoldPhase.READY_ACTIVE,
    }
)

# A2 numeric-entry sub-flow (UX ``auto_bid_edit``): FSM state + draft flag.
_CAH_AWAITING_AUTO_BID_STATE = "cah_awaiting_auto_bid_input"
_CAH_AWAITING_AUTO_BID_ADV_KEY = "cah_awaiting_auto_bid_adv_id"
_AUTO_BID_ENTRY_PROMPT = (
    "Введите новую ставку Auto (число больше 0) и отправьте сообщение в чат."
)


def _resolve_auto_bid_entry_adv_id(adv_or_id: Any) -> int | None:
    """Извлечь adv_setting_original_id из int / AdvSetting-like / None."""
    if adv_or_id is None:
        return None
    if isinstance(adv_or_id, bool):
        return None
    if isinstance(adv_or_id, int):
        return int(adv_or_id)
    raw_id = getattr(adv_or_id, "id", None)
    if raw_id is not None:
        try:
            return int(raw_id)
        except (TypeError, ValueError):
            return None
    try:
        return int(adv_or_id)
    except (TypeError, ValueError):
        return None


def _parse_auto_bid_text(text: str | None) -> float | None:
    """Распарсить положительную ставку Auto из текста сообщения."""
    if text is None:
        return None
    raw = str(text).strip().replace(",", ".")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return value


async def _maybe_answer(message: Any, text: str, **kwargs: Any) -> None:
    """Вызвать ``message.answer``, если у объекта есть callable ``answer``.

    Args:
        message: aiogram Message (или duck-typed объект с ``answer``).
        text: текст ответа.
        **kwargs: доп. аргументы ``answer`` (например ``reply_markup``).
    """
    answer = getattr(message, "answer", None)
    if not callable(answer):
        return
    result = answer(text, **kwargs)
    if inspect.isawaitable(result):
        await result


async def _notify_callback_user(query: CallbackQuery, text: str | None) -> None:
    """Краткое пояснение в чат после ACK middleware (не CallbackQuery.answer).

    ``ImmediateCallbackAnswerUpdateMiddleware`` уже ответил на CallbackQuery.
    Handlers не вызывают ``query.answer()``; user-visible toast/alert →
    ``message.answer`` или ``bot.send_message`` (см. docks/CALLBACK_ANSWER_POLICY.md).

    Args:
        query: CallbackQuery текущего хендлера.
        text: текст уведомления; пустой/None — no-op.
    """
    if not text:
        return
    msg = query.message
    answer = getattr(msg, "answer", None) if msg is not None else None
    if callable(answer):
        result = answer(text)
        if inspect.isawaitable(result):
            await result
        return
    bot = getattr(query, "bot", None)
    send = getattr(bot, "send_message", None) if bot is not None else None
    if not callable(send):
        return
    chat_id = getattr(getattr(query, "from_user", None), "id", None)
    if chat_id is None:
        return
    result = send(chat_id, text)
    if inspect.isawaitable(result):
        await result


def _default_auto_bid(adv: AdvSetting) -> float:
    cpm = getattr(adv, "cpm", None)
    if cpm is not None and float(cpm) > 0:
        return float(cpm)
    return 100.0


def _draft_auto_bid(draft: dict[str, Any], adv: AdvSetting) -> float:
    """Ставка Auto из FSM-черновика или default по кампании."""
    raw = draft.get("auto_bid")
    if raw is not None:
        return float(raw)
    return _default_auto_bid(adv)


def _keyword_candidates(
    adv: AdvSetting,
    *,
    calculated_keywords: list[Any] | None = None,
) -> list[str]:
    """Кандидаты для S1: snapshot → confirmed → live eligible read-model.

    После epoch-managed Enable snapshot/confirmed пусты (``process_ab_setup``
    no-op). Тогда берём PASS-ключи из CalculatedKeyword / injected source
    (PFO ≤ max CPO, ≥100 показов) — для явного user select, без auto-confirm
    (decision ``ab-hold-confirmed-epoch-parameters-sot`` §1).

    Args:
        adv: кампания / AdvSetting-like.
        calculated_keywords: опциональный eligibility source; иначе transient
            ``AB_HOLD_S1_SOURCE_KEYWORDS_ATTR`` (выставляет async resolve).

    Returns:
        Список текстов кандидатов (может быть пустым, если eligibility нет).
    """
    snapshot_raw = cast(
        list[str],
        getattr(adv, "card_ab_hold_allowed_phrases_snapshot", None) or [],
    )
    if snapshot_raw:
        return snapshot_raw
    confirmed = cast(
        list[str],
        getattr(adv, "card_ab_hold_confirmed_keywords_json", None) or [],
    )
    if confirmed:
        return confirmed
    source = calculated_keywords
    if source is None:
        raw_source = getattr(adv, AB_HOLD_S1_SOURCE_KEYWORDS_ATTR, None)
        if raw_source is not None:
            source = list(raw_source)
    if not source:
        return []
    max_pfo = float(getattr(adv, "max_price_for_order", None) or 0)
    return eligible_keyword_texts_for_confirm(
        source,
        max_pay_for_order=max_pfo,
    )


async def _resolve_keyword_candidates(adv: AdvSetting) -> list[str]:
    """S1 candidates с live eligibility load при пустых snapshot/confirmed.

    Загружает CalculatedKeyword через тот же UI read-model, что keyboard
    (``get_keywords_for_keyboard``), кэширует source на ``adv`` и возвращает
    PASS-тексты. Не пишет PG snapshot и не auto-confirm.
    """
    existing = _keyword_candidates(adv)
    if existing:
        return existing
    from app.client_bot.utils import get_keywords_for_keyboard

    try:
        keywords = await get_keywords_for_keyboard(adv)
    except Exception:
        logger.exception(
            "[adv_setting_id=%s] S1 eligible keyword load failed",
            getattr(adv, "id", None),
        )
        return []
    setattr(adv, AB_HOLD_S1_SOURCE_KEYWORDS_ATTR, list(keywords))
    return _keyword_candidates(adv)


FactualPositionsMap: TypeAlias = dict[str, float]
"""Live W3 factual positions: keyword text → raw ``KeywordStat.position`` (float)."""

KeywordsForKeyboardLoader: TypeAlias = Callable[
    [AdvSetting],
    Awaitable[list[CalculatedKeyword]],
]
"""Production keyboard/CH loader seam for ``_load_factual_positions``."""


def _tp_rows_and_exclusions(
    adv: AdvSetting,
    positions: FactualPositionsMap,
) -> tuple[list[tuple[str, int, int]], list[tuple[str, str]]]:
    """Построить valid W3 rows и причины исключения ключей.

    Fact — live read-model (передаётся снаружи), не durable epoch SoT.
    Target — confirmed TP эпохи, иначе proposed из ``positions``.

    Decision ``ab-hold-confirmed-epoch-parameters-sot`` §2: факт обновляется
    при каждом отображении и MUST NOT читаться из фантомного PG-поля на AdvSetting.

    Production ``positions`` приходят из ``_load_factual_positions`` как
    ``dict[str, float]`` (``KeywordStat.position`` always ``float``). Локальные
    ``try/except`` при ``float(position)`` — только для unit/injectable seams с
    duck-typed doubles; prod-path не полагается на ``None`` в значениях dict.
    """
    keywords = cast(
        list[str],
        list(getattr(adv, "card_ab_hold_confirmed_keywords_json", None) or []),
    )
    confirmed_tp = cast(
        dict[str, int],
        dict(getattr(adv, "card_ab_hold_confirmed_target_places_json", None) or {}),
    )
    finite_positive_positions: dict[str, float] = {}
    for keyword, position in positions.items():
        try:
            numeric_position = float(position)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric_position) and numeric_position > 0:
            finite_positive_positions[keyword] = numeric_position
    proposed = propose_target_places_from_positions(finite_positive_positions)
    rows: list[tuple[str, int, int]] = []
    exclusions: list[tuple[str, str]] = []
    for kw in keywords:
        raw_position = positions.get(kw)
        if raw_position is None:
            exclusions.append((kw, "фактическая позиция недоступна"))
            continue
        try:
            raw_fact = float(raw_position)
        except (TypeError, ValueError):
            exclusions.append((kw, "фактическая позиция недоступна"))
            continue
        if not math.isfinite(raw_fact):
            exclusions.append((kw, "фактическая позиция недоступна"))
            continue
        if raw_fact <= 0:
            exclusions.append((kw, "фактическая позиция неположительная"))
            continue
        fact = int(raw_fact)
        raw_target = confirmed_tp.get(kw, proposed.get(kw, fact))
        try:
            target = int(raw_target)
        except (TypeError, ValueError):
            exclusions.append((kw, "предложенная цель недоступна"))
            continue
        if target <= 0:
            exclusions.append((kw, "предложенная цель недоступна"))
            continue
        rows.append((kw, fact, target))
    return rows, exclusions


def _tp_rows_from_adv(
    adv: AdvSetting,
    positions: FactualPositionsMap,
) -> list[tuple[str, int, int]]:
    """Строки W3 только для finite positive factual positions.

    Args:
        adv: кампания с текущим confirmed keyword-set.
        positions: live factual-position read-model.

    Returns:
        Valid rows ``(keyword, factual_position, target_place)``. Ключи без
        положительной позиции намеренно не попадают в результат и не могут
        породить ``target_place=0``.
    """
    rows, _ = _tp_rows_and_exclusions(adv, positions)
    return rows


def _has_complete_factual_position_read(
    adv: AdvSetting,
    positions: FactualPositionsMap,
) -> bool:
    """Проверить, покрывает ли live-read весь durable keyword-set.

    Наличие ключа, а не валидность его позиции, определяет полноту чтения:
    полный authoritative read может содержать ``0`` или отрицательную
    позицию, и тогда явное исключение ключа остаётся допустимым.
    """
    confirmed_keywords = set(
        cast(
            list[str],
            getattr(adv, "card_ab_hold_confirmed_keywords_json", None) or [],
        )
    )
    return confirmed_keywords.issubset(positions)


_ACTOR_UNSET = object()
"""Sentinel: ``_load_adv`` caller intentionally skips PG ownership re-check.

Используется read-only redraw/pagination handlers и post-write re-read после
успешного write-gate. См. блок «Telegram (TG) callback ownership» ниже."""

# ---------------------------------------------------------------------------
# Telegram (TG) callback ownership (card-ab-hold confirm-flow)
# ---------------------------------------------------------------------------
# Платформа UI — Telegram / TG (aiogram). Это не HTTP API по adv_setting_id.
#
# Write-path (PG/epoch mutations): handlers MUST вызывать
# ``_load_adv(..., telegram_user_id=<actor>)`` — foreign actor → ``None``,
# neutral notice, без durable write (``CAH-OWN-FOREIGN-CONFIRM`` / DISABLE).
#
# Read-path (pagination, refresh, back, open-current-step, post-write re-read):
# handlers вызывают ``_load_adv(adv_id)`` без ``telegram_user_id`` →
# ``_ACTOR_UNSET``. Это намеренно, не fail-open ownership bypass:
#
# - CallbackQuery в Telegram нельзя invoke удалённо, зная только adv_id.
# - Callback приходит только после нажатия inline-кнопки на сообщении,
#   видимом этому пользователю в этом чате (обычно private Owner ↔ bot).
# - Пересланные сообщения с inline-клавиатурой не дают чужому пользователю
#   replay callback с чужим ``adv_setting_original_id`` (TG не пересылает
#   CallbackQuery; нет cross-user spy «угадал id → прочитал чужой confirm»).
# - Upstream entry: ``AdvSettingMenu`` / ``CardAbHoldMenu`` открываются из
#   cabinet-scoped navigation (``wb_user_cabinet``), не из произвольного id.
#
# Bugbot: отсутствие ``telegram_user_id`` на read-only handler — NOT a security
# defect для текущего Telegram UX; не эскалировать без нового product spec
# (например, group-chat campaign UI с другой моделью доступа).
# ---------------------------------------------------------------------------


def _raw_cluster_position_for_w3(kw: CalculatedKeyword) -> float:
    """Сырая factual position для W3 (не ``CalculatedKeyword.position``).

    Production keyboard path возвращает ``CalculatedKeyword`` с
    ``KeywordStat.position: float`` (Pydantic, non-optional). Ключ без данных
    в CH получает ``make_zero_keyword_stat`` → ``0.0``, не ``None``; ``NULL`` из
    CH отсекается на ``KeywordStat.model_validate`` до этого read-path.

    Намеренно читаем ``cluster_stat.position``, а не property ``position``:
    property делает ``max(round(x), 1)`` и маскирует ``0``/invalid — W3 exclusions
    должны видеть сырое значение (decision ``ab-hold-confirmed-epoch-parameters-sot``
    §2).

    ``0``, отрицательные и non-finite значения здесь не считаются ошибкой: их
    обрабатывает ``_tp_rows_and_exclusions`` (exclusion copy, без crash).
    """
    return kw.cluster_stat.position


async def _load_factual_positions(
    adv: AdvSetting,
    *,
    keywords_loader: KeywordsForKeyboardLoader | None = None,
) -> FactualPositionsMap:
    """Текущие наблюдаемые позиции ключей (Telegram UI read-model).

    Источник — тот же путь, что keyword-клавиатура бота
    (``get_keywords_for_keyboard`` → ``fetch_keywords_from_database`` / CH+PG),
    не Redis-only snapshot и не колонка AdvSetting.

    Типобезопасный prod-contract:
    - loader возвращает ``list[CalculatedKeyword]``;
    - каждая позиция — ``float`` через ``_raw_cluster_position_for_w3``;
    - ``None`` для ``cluster_stat.position`` в prod-path недостижим (см. docstring
      helper'а); invalid numeric semantics — downstream в ``_tp_rows_and_exclusions``.

    Injectable ``keywords_loader`` (default ``get_keywords_for_keyboard``)
    делает CH/PG boundary тестируемой без module-level patch: unit-тесты могут
    подставить duck-typed loader, production path при ``None`` не меняется.

    Args:
        adv: кампания, для которой читаются позиции.
        keywords_loader: optional override keyboard/CH read-model loader.

    Returns:
        Mapping ``keyword_text → raw cluster position`` (``float``, может быть
        ``0.0`` или non-finite — фильтрация на шаге W3 validator).
    """
    from app.client_bot.utils import get_keywords_for_keyboard

    loader: KeywordsForKeyboardLoader = (
        keywords_loader
        if keywords_loader is not None
        else get_keywords_for_keyboard
    )
    keywords: list[CalculatedKeyword] = await loader(adv)
    out: FactualPositionsMap = {}
    for kw in keywords:
        out[kw.text] = _raw_cluster_position_for_w3(kw)
    return out


async def _render_w3_confirmed(
    query: CallbackQuery,
    adv: AdvSetting,
    *,
    adv_id: int,
    revision: int,
    page: int,
) -> None:
    """Read-only W3-confirmed после durable TP confirm (§7)."""
    positions = await _load_factual_positions(adv)
    rows = _tp_rows_from_adv(adv, positions)
    page_rows, norm_page, total_pages = paginate(rows, page)
    text = build_w3_confirmed_text(
        rows=page_rows, page=norm_page, total_pages=total_pages
    )
    kb = build_w3_confirmed_keyboard(
        adv_id=adv_id, rows=rows, revision=revision, page=norm_page
    )
    await _edit_confirm_screen(query, text, kb)


async def _answer_stale(
    query: CallbackQuery,
    *,
    adv_id: int,
    action_id: str,
    expected: int,
    received: int,
    phase: CardAbHoldPhase | None,
) -> None:
    logger.warning(
        "[adv_setting_id=%s] stale confirm callback action=%s expected=%s received=%s phase=%s",
        adv_id,
        action_id,
        expected,
        received,
        phase.value if phase else None,
    )
    await _notify_callback_user(query, STALE_TOAST)


async def _edit_confirm_screen(
    query: CallbackQuery,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    msg = query.message
    if isinstance(msg, Message):
        await msg.edit_text(text, reply_markup=keyboard)


async def _check_stale(
    query: CallbackQuery,
    adv: AdvSetting,
    callback_revision: int,
    state: FSMContext,
    *,
    action_id: str,
) -> bool:
    """True если callback устарел — ответ toast, caller должен redraw."""
    phase = normalize_card_ab_hold_phase(getattr(adv, "card_ab_hold_phase", None))
    if phase in _GENERATION_PHASES or normalize_card_ab_hold_mode(
        adv.card_ab_hold_mode
    ) == CardAbHoldMode.ACTIVE:
        gen = int(getattr(adv, "card_ab_hold_generation", 0) or 0)
        if await is_stale_generation(gen, callback_revision):
            await _answer_stale(
                query,
                adv_id=int(adv.id),
                action_id=action_id,
                expected=gen,
                received=callback_revision,
                phase=phase,
            )
            return True
        return False
    if await is_stale_revision(state, int(adv.id), callback_revision):
        current = await get_revision(state, int(adv.id))
        await _answer_stale(
            query,
            adv_id=int(adv.id),
            action_id=action_id,
            expected=current,
            received=callback_revision,
            phase=phase,
        )
        return True
    return False


async def _render_for_adv(
    query: CallbackQuery,
    adv: AdvSetting,
    state: FSMContext,
) -> None:
    """Нарисовать актуальный экран по durable phase + FSM draft."""
    draft = await load_draft(state, int(adv.id))
    phase = normalize_card_ab_hold_phase(getattr(adv, "card_ab_hold_phase", None))
    mode = normalize_card_ab_hold_mode(adv.card_ab_hold_mode)
    revision = await get_revision(state, int(adv.id))
    adv_id = int(adv.id)

    if draft.get("cancel_dialog_open"):
        step = ConfirmStep(draft.get("return_step", ConfirmStep.S1.value))
        text = build_cancel_dialog_text(step=step)
        kb = build_cancel_dialog_keyboard(
            adv_id=adv_id, step=step, revision=revision, page=int(draft.get("page") or 0)
        )
        await _edit_confirm_screen(query, text, kb)
        return

    if draft.get("summary_visible"):
        text = build_summary_text(phase=phase)
        kb = build_summary_keyboard(
            adv_id=adv_id,
            return_step=str(draft.get("return_step", ConfirmStep.S1.value)),
            revision=revision,
        )
        await _edit_confirm_screen(query, text, kb)
        return

    if phase == CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM:
        keywords = await _resolve_keyword_candidates(adv)
        page = int(draft.get("page") or 0)
        _, norm_page, total_pages = paginate(keywords, page)
        text = build_s1_text(
            keywords=keywords[norm_page * 10 : norm_page * 10 + 10],
            page=norm_page,
            total_pages=total_pages,
            draft=draft,
            is_s1b=False,
        )
        kb = build_s1_keyboard(
            adv_id=adv_id,
            all_keywords=keywords,
            draft=draft,
            revision=revision,
            page=norm_page,
            is_s1b=False,
        )
        await _edit_confirm_screen(query, text, kb)
        return

    if phase == CardAbHoldPhase.WARM_UP:
        confirmed = getattr(adv, "card_ab_hold_confirmed_keywords_json", None)
        if draft.get("return_step") == ConfirmStep.S1B.value or (
            confirmed and draft.get("keyword_included")
        ):
            keywords = list(confirmed or _keyword_candidates(adv))
            page = int(draft.get("page") or 0)
            _, norm_page, total_pages = paginate(keywords, page)
            slice_kw = keywords[norm_page * 10 : norm_page * 10 + 10]
            text = build_s1_text(
                keywords=slice_kw,
                page=norm_page,
                total_pages=total_pages,
                draft=draft,
                is_s1b=True,
            )
            kb = build_s1_keyboard(
                adv_id=adv_id,
                all_keywords=keywords,
                draft=draft,
                revision=revision,
                page=norm_page,
                is_s1b=True,
            )
            await _edit_confirm_screen(query, text, kb)
            return
        duration = int(
            draft.get("duration_hours")
            or getattr(adv, "card_ab_hold_warmup_duration_hours", None)
            or DEFAULT_WARMUP_HOURS
        )
        started = getattr(adv, "card_ab_hold_warmup_started_at", None)
        if started is None and not getattr(adv, "card_ab_hold_confirmed_keywords_json", None):
            text = build_s2_text(duration_hours=duration)
            kb = build_s2_keyboard(adv_id=adv_id, revision=revision)
            await _edit_confirm_screen(query, text, kb)
            return
        if started is None:
            text = build_s2_text(duration_hours=duration)
            kb = build_s2_keyboard(adv_id=adv_id, revision=revision)
            await _edit_confirm_screen(query, text, kb)
            return
        text = build_s3_text(
            started_at=started,
            duration_hours=int(
                getattr(adv, "card_ab_hold_warmup_duration_hours", None)
                or duration
            ),
        )
        kb = build_s3_keyboard(adv_id=adv_id, revision=revision)
        await _edit_confirm_screen(query, text, kb)
        return

    if phase == CardAbHoldPhase.AWAITING_TP_CONFIRM:
        positions = await _load_factual_positions(adv)
        rows, exclusions = _tp_rows_and_exclusions(adv, positions)
        page = int(draft.get("page") or 0)
        page_rows, norm_page, total_pages = paginate(rows, page)
        text = build_w3_propose_text(
            rows=page_rows,
            page=norm_page,
            total_pages=total_pages,
            exclusions=exclusions,
        )
        kb = build_w3_propose_keyboard(
            adv_id=adv_id, rows=rows, revision=revision, page=norm_page
        )
        await _edit_confirm_screen(query, text, kb)
        return

    if should_show_w3_confirmed_read_only(adv, draft) and phase in (
        CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM,
        CardAbHoldPhase.AWAITING_AUTO_BID_CONFIRM,
    ):
        await _render_w3_confirmed(
            query,
            adv,
            adv_id=adv_id,
            revision=revision,
            page=int(draft.get("page") or 0),
        )
        return

    if phase == CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM:
        text = build_a1_text()
        kb = build_a1_keyboard(adv_id=adv_id, revision=revision)
        await _edit_confirm_screen(query, text, kb)
        return

    if phase == CardAbHoldPhase.AWAITING_AUTO_BID_CONFIRM:
        bid = _draft_auto_bid(draft, adv)
        text = build_a2_text(auto_bid=bid)
        kb = build_a2_keyboard(adv_id=adv_id, revision=revision, auto_bid=bid)
        await _edit_confirm_screen(query, text, kb)
        return

    sync_status = normalize_card_ab_hold_sync_status(
        getattr(adv, "card_ab_hold_sync_status", None)
    )
    generation = int(getattr(adv, "card_ab_hold_generation", 0) or 0)

    if phase == CardAbHoldPhase.PENDING_INTENT or (
        phase == CardAbHoldPhase.WB_SYNC and sync_status == CardAbHoldSyncStatus.PENDING
    ):
        text = build_p1_text()
        kb = build_p1_keyboard(adv_id=adv_id, generation=generation)
        await _edit_confirm_screen(query, text, kb)
        return

    if phase == CardAbHoldPhase.WB_SYNC and sync_status == CardAbHoldSyncStatus.PARTIAL:
        text = build_p2_text()
        kb = build_p2_keyboard(adv_id=adv_id, generation=generation)
        await _edit_confirm_screen(query, text, kb)
        return

    if mode == CardAbHoldMode.ACTIVE or phase == CardAbHoldPhase.READY_ACTIVE:
        text = build_h1_text(degraded=bool(getattr(adv, "card_ab_hold_degraded", False)))
        kb = build_h1_keyboard(adv_id=adv_id, generation=generation)
        await _edit_confirm_screen(query, text, kb)
        return

    text = build_summary_text(phase=phase)
    kb = build_summary_keyboard(
        adv_id=adv_id,
        return_step=ConfirmStep.S1.value,
        revision=revision,
    )
    await _edit_confirm_screen(query, text, kb)


async def _load_adv_in_session(
    session: AsyncSession,
    adv_setting_original_id: int,
) -> AdvSetting | None:
    """Загрузить AdvSetting в переданной PURE_READ session.

    Args:
        session: injectable async session.
        adv_setting_original_id: ``AdvSetting.id``.

    Returns:
        AdvSetting или None.
    """
    return await session.scalar(
        select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
    )


async def _load_adv(
    adv_setting_original_id: int,
    *,
    telegram_user_id: int | None | object = _ACTOR_UNSET,
) -> AdvSetting | None:
    """Загрузить AdvSetting; опционально — cabinet ownership gate для write-path.

    Два режима (см. module-level «Telegram callback ownership»):

    1. **Write-gate** — caller передаёт ``telegram_user_id`` (int). Foreign /
       missing actor → ``None`` (fail-closed до PG mutation).
    2. **Read-redraw** — caller omits ``telegram_user_id`` (default
       ``_ACTOR_UNSET``). Ownership не перепроверяется: redraw опирается на
       Telegram visibility inline callback + upstream ``wb_user_cabinet`` menu
       path. Это не «чтение по угаданному adv_id» извне Telegram.

    Args:
        adv_setting_original_id: ``AdvSetting.id`` из callback_data.
        telegram_user_id: Telegram actor для write-gate; omit для read-redraw
            и post-write re-read сразу после успешного write-gate в том же
            handler.

    Returns:
        AdvSetting или ``None`` (row missing / foreign actor при write-gate).
    """
    async with sm(read_only=True) as session:
        adv = await _load_adv_in_session(session, adv_setting_original_id)
        if adv is None or telegram_user_id is _ACTOR_UNSET:
            return adv
        if isinstance(telegram_user_id, bool) or not isinstance(telegram_user_id, int):
            return None
        owner = await get_wb_user_cabinet_for_adv_and_telegram(
            session, adv, telegram_user_id
        )
        if owner is None:
            logger.info(
                "[adv_setting_id=%s] foreign A/B Hold callback rejected",
                adv_setting_original_id,
            )
            return None
        return adv


_UI_HIDDEN_NOTICE = "Доступно только при включённом боте"


async def _load_adv_for_write(
    query: CallbackQuery,
    adv_setting_original_id: int,
) -> AdvSetting | None:
    """Write-path load с fail-closed actor + cabinet ownership gate.

    Используется confirm write-handlers перед PG/epoch mutation. Missing/invalid
    Telegram actor → ``MISSING_ACTOR_NOTICE``; foreign/missing row →
    ``_UI_HIDDEN_NOTICE``.

    Args:
        query: CallbackQuery write-handler'а.
        adv_setting_original_id: ``AdvSetting.id`` из callback_data.

    Returns:
        AdvSetting после ownership gate или ``None`` (user уже уведомлён).
    """
    actor_id = _callback_actor_id(query)
    if actor_id is None:
        await _notify_callback_user(query, MISSING_ACTOR_NOTICE)
        return None
    adv = await _load_adv(
        adv_setting_original_id,
        telegram_user_id=actor_id,
    )
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await _notify_callback_user(query, _UI_HIDDEN_NOTICE)
        return None
    return adv


async def _abort_epoch_mode_off_in_session(
    session: AsyncSession,
    adv_setting_id: int,
    *,
    commit: bool = True,
) -> AdvSetting | None:
    """Mode → OFF + clear allowed snapshot в переданной WRITE session.

    Args:
        session: injectable async write session.
        adv_setting_id: ``AdvSetting.id``.
        commit: выполнить ли commit немедленно. EXIT передаёт ``False``,
            чтобы объединить mode/snapshot и epoch reset в одну транзакцию.

    Returns:
        Обновлённый AdvSetting или None.
    """
    row = await session.scalar(
        select(AdvSetting)
        .options(noload(AdvSetting.wb_cabinet))
        .where(AdvSetting.id == adv_setting_id)
    )
    if row is None:
        return None
    row.card_ab_hold_mode = CardAbHoldMode.OFF.value
    row.card_ab_hold_allowed_phrases_snapshot = empty_allowed_snapshot()
    if commit:
        await session.commit()
    return row


async def _abort_epoch_to_off(adv: AdvSetting) -> None:
    """Abort epoch attempt → OFF (§8, nothing durable to clear on fresh S1)."""
    async with sm(read_only=False) as session:
        _ = await _abort_epoch_mode_off_in_session(
            session,
            int(adv.id),
            commit=False,
        )
        await clear_epoch_on_exit_in_session(
            session,
            int(adv.id),
            commit=False,
        )
        await session.commit()
    await CardAbHoldSignalRedisCache(adv).clear()
    await CardAbHoldSetupBlockRedisCache(adv).clear()


@card_ab_hold_confirm_router.callback_query(CahKeywordToggle.filter())
async def on_keyword_toggle(
    query: CallbackQuery,
    callback_data: CahKeywordToggle,
    state: FSMContext,
) -> None:
    adv = await _load_adv_for_write(query, callback_data.adv_setting_original_id)
    if adv is None:
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="keyword_toggle"
    ):
        await _render_for_adv(query, adv, state)
        return
    keywords = await _resolve_keyword_candidates(adv)
    if callback_data.keyword_idx < 0 or callback_data.keyword_idx >= len(keywords):
        await _render_for_adv(query, adv, state)
        return
    kw = keywords[callback_data.keyword_idx]
    await toggle_keyword_inclusion(state, int(adv.id), kw)
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahPageNav.filter())
async def on_page_nav(
    query: CallbackQuery,
    callback_data: CahPageNav,
    state: FSMContext,
) -> None:
    # Read-redraw: ownership via Telegram callback visibility (see module policy).
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await _notify_callback_user(query, "Доступно только при включённом боте")
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="page_nav"
    ):
        await _render_for_adv(query, adv, state)
        return
    new_page = callback_data.page + (
        1 if callback_data.direction == "n" else -1
    )
    await set_page(state, int(adv.id), new_page, bump=True)
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahKeywordSetConfirm.filter())
async def on_keyword_set_confirm(
    query: CallbackQuery,
    callback_data: CahKeywordSetConfirm,
    state: FSMContext,
) -> None:
    adv = await _load_adv_for_write(query, callback_data.adv_setting_original_id)
    if adv is None:
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="keyword_set_confirm"
    ):
        await _render_for_adv(query, adv, state)
        return
    draft = await load_draft(state, int(adv.id))
    keywords = await _resolve_keyword_candidates(adv)
    selected = selected_keywords(keywords, draft)
    if not selected:
        await _notify_callback_user(query, "Выберите хотя бы один ключ")
        return
    duration = int(draft.get("duration_hours") or DEFAULT_WARMUP_HOURS)
    await confirm_keyword_set_and_start_warmup(
        int(adv.id), selected, duration_hours=duration
    )
    draft["return_step"] = ConfirmStep.S2.value
    draft["keyword_included"] = {}
    await save_draft(state, int(adv.id), draft)
    await bump_revision(state, int(adv.id))
    await _notify_callback_user(query, "Набор ключей подтверждён")
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahWarmupDurationPreset.filter())
async def on_warmup_preset(
    query: CallbackQuery,
    callback_data: CahWarmupDurationPreset,
    state: FSMContext,
) -> None:
    adv = await _load_adv_for_write(query, callback_data.adv_setting_original_id)
    if adv is None:
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="warmup_duration_preset"
    ):
        await _render_for_adv(query, adv, state)
        return
    draft = await load_draft(state, int(adv.id))
    draft["duration_hours"] = int(callback_data.hours)
    draft["revision"] = int(draft.get("revision") or 1) + 1
    await save_draft(state, int(adv.id), draft)
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahWarmupDurationConfirm.filter())
async def on_warmup_duration_confirm(
    query: CallbackQuery,
    callback_data: CahWarmupDurationConfirm,
    state: FSMContext,
) -> None:
    adv = await _load_adv_for_write(query, callback_data.adv_setting_original_id)
    if adv is None:
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="warmup_duration_confirm"
    ):
        await _render_for_adv(query, adv, state)
        return
    draft = await load_draft(state, int(adv.id))
    hours = int(draft.get("duration_hours") or DEFAULT_WARMUP_HOURS)
    await set_warmup_duration(int(adv.id), hours)
    await bump_revision(state, int(adv.id))
    await _notify_callback_user(query, "Длительность прогрева подтверждена")
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahWarmupStatusRefresh.filter())
async def on_warmup_refresh(
    query: CallbackQuery,
    callback_data: CahWarmupStatusRefresh,
    state: FSMContext,
) -> None:
    # Read-redraw: ownership via Telegram callback visibility (see module policy).
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await _notify_callback_user(query, "Доступно только при включённом боте")
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="warmup_status_refresh"
    ):
        await _render_for_adv(query, adv, state)
        return
    await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahKeywordEditOpen.filter())
async def on_keyword_edit_open(
    query: CallbackQuery,
    callback_data: CahKeywordEditOpen,
    state: FSMContext,
) -> None:
    adv = await _load_adv_for_write(query, callback_data.adv_setting_original_id)
    if adv is None:
        return
    phase = normalize_card_ab_hold_phase(getattr(adv, "card_ab_hold_phase", None))
    if phase != CardAbHoldPhase.WARM_UP:
        await _answer_stale(
            query,
            adv_id=int(adv.id),
            action_id="keyword_edit_open",
            expected=0,
            received=callback_data.revision,
            phase=phase,
        )
        await _render_for_adv(query, adv, state)
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="keyword_edit_open"
    ):
        await _render_for_adv(query, adv, state)
        return
    draft = await load_draft(state, int(adv.id))
    confirmed = list(getattr(adv, "card_ab_hold_confirmed_keywords_json", None) or [])
    draft["return_step"] = ConfirmStep.S1B.value
    draft["keyword_included"] = {kw: True for kw in confirmed}
    draft["page"] = 0
    draft["revision"] = int(draft.get("revision") or 1) + 1
    await save_draft(state, int(adv.id), draft)
    await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahTpConfirmAll.filter())
async def on_tp_confirm_all(
    query: CallbackQuery,
    callback_data: CahTpConfirmAll,
    state: FSMContext,
) -> None:
    adv = await _load_adv_for_write(query, callback_data.adv_setting_original_id)
    if adv is None:
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="tp_confirm_all"
    ):
        await _render_for_adv(query, adv, state)
        return
    positions = await _load_factual_positions(adv)
    if not _has_complete_factual_position_read(adv, positions):
        await _notify_callback_user(
            query,
            "Не удалось получить фактические позиции всех подтверждённых ключей. "
            "Повторите попытку позже.",
        )
        await _render_for_adv(query, adv, state)
        return
    rows = _tp_rows_from_adv(adv, positions)
    tp_map = {
        kw: target
        for kw, _fact, target in rows
    }
    if not tp_map:
        await _notify_callback_user(
            query,
            "Нет валидных ключей для подтверждения: фактические позиции "
            "отсутствуют или неположительны.",
        )
        await _render_for_adv(query, adv, state)
        return
    try:
        await confirm_target_places(int(adv.id), tp_map)
    except EpochWriteError:
        logger.info(
            "[adv_setting_id=%s] TP confirmation became stale before durable write",
            adv.id,
        )
        await _notify_callback_user(
            query,
            "Состояние подтверждения изменилось. Экран обновлён.",
        )
        current_adv = await _load_adv(callback_data.adv_setting_original_id)
        if current_adv is not None:
            await _render_for_adv(query, current_adv, state)
        return
    await set_w3_confirmed_visible(state, int(adv.id), True)
    await bump_revision(state, int(adv.id))
    await _notify_callback_user(query, "Целевые позиции зафиксированы")
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahContinueToAuto.filter())
async def on_continue_to_auto(
    query: CallbackQuery,
    callback_data: CahContinueToAuto,
    state: FSMContext,
) -> None:
    """W3-confirmed → A1/A2: скрыть read-only экран и показать следующий шаг (§7)."""
    # Read-redraw (+ FSM only): Telegram callback visibility; no PG write.
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await _notify_callback_user(query, "Доступно только при включённом боте")
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="continue_to_auto"
    ):
        await _render_for_adv(query, adv, state)
        return
    await set_w3_confirmed_visible(state, int(adv.id), False)
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahAutoParticipationConfirm.filter())
async def on_auto_participation_confirm(
    query: CallbackQuery,
    callback_data: CahAutoParticipationConfirm,
    state: FSMContext,
) -> None:
    adv = await _load_adv_for_write(query, callback_data.adv_setting_original_id)
    if adv is None:
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="auto_participation_confirm"
    ):
        await _render_for_adv(query, adv, state)
        return
    participates = bool(callback_data.participates)
    await confirm_auto_participation(int(adv.id), participates)
    if not participates:
        await confirm_auto_bid(int(adv.id), 0.0)
        await _notify_callback_user(query, "Участие Auto: нет. Создание intent…")
    else:
        await _notify_callback_user(query, "Участие Auto подтверждено")
    await bump_revision(state, int(adv.id))
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahAutoBidConfirm.filter())
async def on_auto_bid_confirm(
    query: CallbackQuery,
    callback_data: CahAutoBidConfirm,
    state: FSMContext,
) -> None:
    adv = await _load_adv_for_write(query, callback_data.adv_setting_original_id)
    if adv is None:
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="auto_bid_confirm"
    ):
        await _render_for_adv(query, adv, state)
        return
    draft = await load_draft(state, int(adv.id))
    bid = _draft_auto_bid(draft, adv)
    await confirm_auto_bid(int(adv.id), bid)
    await bump_revision(state, int(adv.id))
    await _notify_callback_user(query, "Ставка Auto подтверждена")
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahAutoBidEdit.filter())
async def on_auto_bid_edit(
    query: CallbackQuery,
    callback_data: CahAutoBidEdit,
    state: FSMContext,
) -> None:
    """A2 «Изменить значение»: открыть numeric-entry sub-flow для draft Auto bid.

    UX ``auto_bid_edit`` — пользователь вводит ставку сообщением; значение
    пишется в FSM-черновик (``draft["auto_bid"]``) через
    ``on_auto_bid_numeric_message``, confirm по-прежнему через
    ``CahAutoBidConfirm``.
    """
    adv = await _load_adv_for_write(query, callback_data.adv_setting_original_id)
    if adv is None:
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="auto_bid_edit"
    ):
        await _render_for_adv(query, adv, state)
        return
    draft = await load_draft(state, int(adv.id))
    current_bid = _draft_auto_bid(draft, adv)
    draft["awaiting_auto_bid_input"] = True
    await save_draft(state, int(adv.id), draft)
    await state.update_data({_CAH_AWAITING_AUTO_BID_ADV_KEY: int(adv.id)})
    await state.set_state(_CAH_AWAITING_AUTO_BID_STATE)
    prompt = (
        f"{_AUTO_BID_ENTRY_PROMPT} Текущая: {current_bid:g}."
    )
    if isinstance(query.message, Message):
        await query.message.answer(prompt)
    elif query.bot is not None:
        # Fallback: rare path without callback message object.
        chat_id = getattr(getattr(query, "from_user", None), "id", None)
        if chat_id is not None:
            await query.bot.send_message(chat_id, prompt)


@card_ab_hold_confirm_router.message(StateFilter(_CAH_AWAITING_AUTO_BID_STATE))
async def on_auto_bid_numeric_message(
    message: Message,
    state: FSMContext,
    adv_or_id: Any = None,
) -> None:
    """Принять числовой ввод ставки Auto в A2 numeric-entry и сохранить в draft.

    Discoverable apply path для UX ``auto_bid_edit``: парсит текст сообщения и
    пишет ``draft["auto_bid"]`` через ``save_draft``. Опциональный третий
    аргумент — AdvSetting / id (unit-тесты / прямой вызов).

    Args:
        message: входящее сообщение с числом.
        state: FSM пользователя (черновик confirm-flow).
        adv_or_id: опционально id кампании или AdvSetting-like.
    """
    data = await state.get_data()
    adv_id = _resolve_auto_bid_entry_adv_id(adv_or_id)
    if adv_id is None:
        adv_id = _resolve_auto_bid_entry_adv_id(data.get(_CAH_AWAITING_AUTO_BID_ADV_KEY))
    if adv_id is None:
        await _maybe_answer(
            message,
            "Сессия ввода ставки устарела. Нажмите «Изменить значение» снова.",
        )
        await state.set_state(None)
        return

    bid = _parse_auto_bid_text(getattr(message, "text", None))
    if bid is None:
        await _maybe_answer(message, _AUTO_BID_ENTRY_PROMPT)
        return

    draft = await load_draft(state, adv_id)
    draft["auto_bid"] = bid
    draft["awaiting_auto_bid_input"] = False
    draft["revision"] = int(draft.get("revision") or 1) + 1
    await save_draft(state, adv_id, draft)
    await state.set_state(None)
    await state.update_data({_CAH_AWAITING_AUTO_BID_ADV_KEY: None})
    revision = int(draft["revision"])
    text = build_a2_text(auto_bid=bid)
    kb = build_a2_keyboard(adv_id=adv_id, revision=revision, auto_bid=bid)
    await _maybe_answer(message, text, reply_markup=kb)

@card_ab_hold_confirm_router.callback_query(CahSyncStatusRefresh.filter())
async def on_sync_refresh(
    query: CallbackQuery,
    callback_data: CahSyncStatusRefresh,
    state: FSMContext,
) -> None:
    # Read-redraw: ownership via Telegram callback visibility (see module policy).
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await _notify_callback_user(query, "Доступно только при включённом боте")
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="sync_status_refresh"
    ):
        await _render_for_adv(query, adv, state)
        return
    await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahConfirmBack.filter())
async def on_back(
    query: CallbackQuery,
    callback_data: CahConfirmBack,
    state: FSMContext,
) -> None:
    # Read-redraw (+ FSM draft): Telegram callback visibility; no PG write.
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await _notify_callback_user(query, "Доступно только при включённом боте")
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="back"
    ):
        await _render_for_adv(query, adv, state)
        return
    step = callback_data.step
    if step in (ConfirmStep.A1.value, ConfirmStep.A2.value):
        phase = normalize_card_ab_hold_phase(getattr(adv, "card_ab_hold_phase", None))
        if phase in (
            CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM,
            CardAbHoldPhase.AWAITING_AUTO_BID_CONFIRM,
        ):
            await set_w3_confirmed_visible(state, int(adv.id), True)
            adv = await _load_adv(callback_data.adv_setting_original_id)
            if adv is not None:
                await _render_for_adv(query, adv, state)
            return
    draft_steps_with_draft = {
        ConfirmStep.S1.value,
        ConfirmStep.S1B.value,
        ConfirmStep.S2.value,
        ConfirmStep.W3_PROPOSE.value,
        ConfirmStep.A1.value,
        ConfirmStep.A2.value,
    }
    if step in draft_steps_with_draft:
        await mark_summary_visible(state, int(adv.id), return_step=step)
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahCancelOpen.filter())
async def on_cancel_open(
    query: CallbackQuery,
    callback_data: CahCancelOpen,
    state: FSMContext,
) -> None:
    adv = await _load_adv_for_write(query, callback_data.adv_setting_original_id)
    if adv is None:
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="cancel_open"
    ):
        await _render_for_adv(query, adv, state)
        return
    draft = await load_draft(state, int(adv.id))
    draft["return_step"] = callback_data.step
    draft["page"] = callback_data.page
    await save_draft(state, int(adv.id), draft)
    await open_cancel_dialog(state, int(adv.id))
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahCancelConfirmNo.filter())
async def on_cancel_no(
    query: CallbackQuery,
    callback_data: CahCancelConfirmNo,
    state: FSMContext,
) -> None:
    adv = await _load_adv_for_write(query, callback_data.adv_setting_original_id)
    if adv is None:
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="cancel_confirm_no"
    ):
        await _render_for_adv(query, adv, state)
        return
    await close_cancel_dialog(state, int(adv.id))
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahCancelConfirmYes.filter())
async def on_cancel_yes(
    query: CallbackQuery,
    callback_data: CahCancelConfirmYes,
    state: FSMContext,
) -> None:
    adv = await _load_adv_for_write(query, callback_data.adv_setting_original_id)
    if adv is None:
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="cancel_confirm_yes"
    ):
        await _render_for_adv(query, adv, state)
        return
    step = callback_data.step
    if step == ConfirmStep.S1B.value:
        await discard_edit_draft_only(state, int(adv.id))
        await _notify_callback_user(query, "Изменения отменены")
    else:
        await reset_draft(state, int(adv.id))
        await _abort_epoch_to_off(adv)
        await _notify_callback_user(query, "A/B тест отменён")
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahOpenCurrentStep.filter())
async def on_open_current_step(
    query: CallbackQuery,
    callback_data: CahOpenCurrentStep,
    state: FSMContext,
) -> None:
    """Read-redraw мост S0/summary → confirm-flow (module TG policy).

    ``callback_data.step`` не участвует в routing: экран выбирается только по
    durable ``adv.card_ab_hold_phase`` + FSM draft в ``_render_for_adv``.
    Поле ``step`` в payload — legacy/schema (S0-клавиатура кладёт ``S1``;
    summary после Back — ``return_step``); stale-gate смотрит ``revision``.
    """
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await _notify_callback_user(query, "Доступно только при включённом боте")
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="open_current_step"
    ):
        await _render_for_adv(query, adv, state)
        return
    await clear_summary(state, int(adv.id))
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahConfirmDisable.filter())
async def on_confirm_disable(
    query: CallbackQuery,
    callback_data: CahConfirmDisable,
    state: FSMContext,
) -> None:
    adv = await _load_adv_for_write(query, callback_data.adv_setting_original_id)
    if adv is None:
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="disable"
    ):
        await _render_for_adv(query, adv, state)
        return
    await reset_draft(state, int(adv.id))
    await _abort_epoch_to_off(adv)
    await _notify_callback_user(query, "A/B Hold выключен")
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)
