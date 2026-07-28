"""Telegram handlers confirm-flow A/B Hold (ux contract §§5–10, §24).

Spec requirements:
- «Confirmation screens paginate keyword lists at a fixed page size»
- «Back preserves the confirmation draft; Cancel is a separate explicit action»
- stale callback → fail-closed redraw (§10)

WB-мутации не выполняются в handlers — sync owned by shop-runner.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy import select

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    CardAbHoldSyncStatus,
    DEFAULT_WARMUP_HOURS,
    normalize_card_ab_hold_sync_status,
    propose_target_places_from_positions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write import (
    clear_epoch_on_exit,
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
    if value <= 0:
        return None
    return value


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


def _tp_rows_from_adv(
    adv: AdvSetting,
    positions: dict[str, float],
) -> list[tuple[str, int, int]]:
    """Строки W3: keyword → (fact, target).

    Fact — live read-model (передаётся снаружи), не durable epoch SoT.
    Target — confirmed TP эпохи, иначе proposed из ``positions``.

    Decision ``ab-hold-confirmed-epoch-parameters-sot`` §2: факт обновляется
    при каждом отображении и MUST NOT читаться из фантомного PG-поля на AdvSetting.
    """
    keywords = cast(
        list[str],
        list(getattr(adv, "card_ab_hold_confirmed_keywords_json", None) or []),
    )
    confirmed_tp = cast(
        dict[str, int],
        dict(getattr(adv, "card_ab_hold_confirmed_target_places_json", None) or {}),
    )
    proposed = propose_target_places_from_positions(positions)
    rows: list[tuple[str, int, int]] = []
    for kw in keywords:
        raw_fact = float(positions.get(kw, 0) or 0)
        fact = int(raw_fact) if raw_fact > 0 else 0
        target = int(confirmed_tp.get(kw, proposed.get(kw, fact)))
        rows.append((kw, fact, target))
    return rows


async def _load_factual_positions(adv: AdvSetting) -> dict[str, float]:
    """Текущие наблюдаемые позиции ключей (Telegram UI read-model).

    Источник — тот же путь, что keyword-клавиатура бота
    (``fetch_keywords_from_database`` / CH+PG), не Redis-only snapshot и не
    колонка AdvSetting. Сырая ``cluster_stat.position`` (без floor-to-1),
    чтобы proposed TP мог отфильтровать non-positive.
    """
    from app.client_bot.utils import get_keywords_for_keyboard

    keywords = await get_keywords_for_keyboard(adv)
    out: dict[str, float] = {}
    for kw in keywords:
        out[str(kw.text)] = float(kw.cluster_stat.position)
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
    await query.answer(STALE_TOAST)


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
        rows = _tp_rows_from_adv(adv, positions)
        page = int(draft.get("page") or 0)
        page_rows, norm_page, total_pages = paginate(rows, page)
        text = build_w3_propose_text(
            rows=page_rows, page=norm_page, total_pages=total_pages
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


async def _load_adv(adv_setting_original_id: int) -> AdvSetting | None:
    async with sm() as session:
        return await session.scalar(
            select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
        )


async def _abort_epoch_to_off(adv: AdvSetting) -> None:
    """Abort epoch attempt → OFF (§8, nothing durable to clear on fresh S1)."""
    async with sm(read_only=False) as session:
        row = await session.scalar(
            select(AdvSetting).where(AdvSetting.id == adv.id)
        )
        if row is None:
            return
        row.card_ab_hold_mode = CardAbHoldMode.OFF.value
        row.card_ab_hold_allowed_phrases_snapshot = empty_allowed_snapshot()
        await session.commit()
    await clear_epoch_on_exit(int(adv.id))
    await CardAbHoldSignalRedisCache(adv).clear()
    await CardAbHoldSetupBlockRedisCache(adv).clear()


@card_ab_hold_confirm_router.callback_query(CahKeywordToggle.filter())
async def on_keyword_toggle(
    query: CallbackQuery,
    callback_data: CahKeywordToggle,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="keyword_toggle"
    ):
        await _render_for_adv(query, adv, state)
        return
    keywords = await _resolve_keyword_candidates(adv)
    if callback_data.keyword_idx < 0 or callback_data.keyword_idx >= len(keywords):
        await query.answer()
        await _render_for_adv(query, adv, state)
        return
    kw = keywords[callback_data.keyword_idx]
    await toggle_keyword_inclusion(state, int(adv.id), kw)
    await query.answer()
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahPageNav.filter())
async def on_page_nav(
    query: CallbackQuery,
    callback_data: CahPageNav,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
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
    await query.answer()
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahKeywordSetConfirm.filter())
async def on_keyword_set_confirm(
    query: CallbackQuery,
    callback_data: CahKeywordSetConfirm,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
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
        await query.answer("Выберите хотя бы один ключ", show_alert=True)
        return
    duration = int(draft.get("duration_hours") or DEFAULT_WARMUP_HOURS)
    await confirm_keyword_set_and_start_warmup(
        int(adv.id), selected, duration_hours=duration
    )
    draft["return_step"] = ConfirmStep.S2.value
    draft["keyword_included"] = {}
    await save_draft(state, int(adv.id), draft)
    await bump_revision(state, int(adv.id))
    await query.answer("Набор ключей подтверждён")
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahWarmupDurationPreset.filter())
async def on_warmup_preset(
    query: CallbackQuery,
    callback_data: CahWarmupDurationPreset,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
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
    await query.answer()
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahWarmupDurationConfirm.filter())
async def on_warmup_duration_confirm(
    query: CallbackQuery,
    callback_data: CahWarmupDurationConfirm,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
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
    await query.answer("Длительность прогрева подтверждена")
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahWarmupStatusRefresh.filter())
async def on_warmup_refresh(
    query: CallbackQuery,
    callback_data: CahWarmupStatusRefresh,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="warmup_status_refresh"
    ):
        await _render_for_adv(query, adv, state)
        return
    await query.answer()
    await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahKeywordEditOpen.filter())
async def on_keyword_edit_open(
    query: CallbackQuery,
    callback_data: CahKeywordEditOpen,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
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
    await query.answer()
    await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahTpConfirmAll.filter())
async def on_tp_confirm_all(
    query: CallbackQuery,
    callback_data: CahTpConfirmAll,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="tp_confirm_all"
    ):
        await _render_for_adv(query, adv, state)
        return
    positions = await _load_factual_positions(adv)
    tp_map = {
        kw: target
        for kw, _fact, target in _tp_rows_from_adv(adv, positions)
    }
    await confirm_target_places(int(adv.id), tp_map)
    await set_w3_confirmed_visible(state, int(adv.id), True)
    await bump_revision(state, int(adv.id))
    await query.answer("Целевые позиции зафиксированы")
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
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="continue_to_auto"
    ):
        await _render_for_adv(query, adv, state)
        return
    await set_w3_confirmed_visible(state, int(adv.id), False)
    await query.answer()
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahAutoParticipationConfirm.filter())
async def on_auto_participation_confirm(
    query: CallbackQuery,
    callback_data: CahAutoParticipationConfirm,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
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
        await query.answer("Участие Auto: нет. Создание intent…")
    else:
        await query.answer("Участие Auto подтверждено")
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
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
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
    await query.answer("Ставка Auto подтверждена")
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
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
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
    await state.update_data(**{_CAH_AWAITING_AUTO_BID_ADV_KEY: int(adv.id)})
    await state.set_state(_CAH_AWAITING_AUTO_BID_STATE)
    await query.answer()
    prompt = (
        f"{_AUTO_BID_ENTRY_PROMPT} Текущая: {current_bid:g}."
    )
    if query.message is not None:
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
        answer = getattr(message, "answer", None)
        if callable(answer):
            await answer("Сессия ввода ставки устарела. Нажмите «Изменить значение» снова.")
        await state.set_state(None)
        return

    bid = _parse_auto_bid_text(getattr(message, "text", None))
    answer = getattr(message, "answer", None)
    if bid is None:
        if callable(answer):
            await answer(_AUTO_BID_ENTRY_PROMPT)
        return

    draft = await load_draft(state, adv_id)
    draft["auto_bid"] = bid
    draft["awaiting_auto_bid_input"] = False
    draft["revision"] = int(draft.get("revision") or 1) + 1
    await save_draft(state, adv_id, draft)
    await state.set_state(None)
    await state.update_data(**{_CAH_AWAITING_AUTO_BID_ADV_KEY: None})
    if not callable(answer):
        return
    revision = int(draft["revision"])
    text = build_a2_text(auto_bid=bid)
    kb = build_a2_keyboard(adv_id=adv_id, revision=revision, auto_bid=bid)
    try:
        await answer(text, reply_markup=kb)
    except TypeError:
        # Unit SimpleNamespace / mocks without reply_markup support.
        await answer(f"Ставка Auto в черновике: {bid:g}. Подтвердите на экране A2.")


@card_ab_hold_confirm_router.callback_query(CahSyncStatusRefresh.filter())
async def on_sync_refresh(
    query: CallbackQuery,
    callback_data: CahSyncStatusRefresh,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="sync_status_refresh"
    ):
        await _render_for_adv(query, adv, state)
        return
    await query.answer()
    await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahConfirmBack.filter())
async def on_back(
    query: CallbackQuery,
    callback_data: CahConfirmBack,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
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
            await query.answer()
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
    await query.answer()
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahCancelOpen.filter())
async def on_cancel_open(
    query: CallbackQuery,
    callback_data: CahCancelOpen,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
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
    await query.answer()
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahCancelConfirmNo.filter())
async def on_cancel_no(
    query: CallbackQuery,
    callback_data: CahCancelConfirmNo,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="cancel_confirm_no"
    ):
        await _render_for_adv(query, adv, state)
        return
    await close_cancel_dialog(state, int(adv.id))
    await query.answer()
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahCancelConfirmYes.filter())
async def on_cancel_yes(
    query: CallbackQuery,
    callback_data: CahCancelConfirmYes,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="cancel_confirm_yes"
    ):
        await _render_for_adv(query, adv, state)
        return
    step = callback_data.step
    if step == ConfirmStep.S1B.value:
        await discard_edit_draft_only(state, int(adv.id))
        await query.answer("Изменения отменены")
    else:
        await reset_draft(state, int(adv.id))
        await _abort_epoch_to_off(adv)
        await query.answer("A/B тест отменён")
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahOpenCurrentStep.filter())
async def on_open_current_step(
    query: CallbackQuery,
    callback_data: CahOpenCurrentStep,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="open_current_step"
    ):
        await _render_for_adv(query, adv, state)
        return
    await clear_summary(state, int(adv.id))
    await query.answer()
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)


@card_ab_hold_confirm_router.callback_query(CahConfirmDisable.filter())
async def on_confirm_disable(
    query: CallbackQuery,
    callback_data: CahConfirmDisable,
    state: FSMContext,
) -> None:
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        await query.answer("Доступно только при включённом боте", show_alert=True)
        return
    if await _check_stale(
        query, adv, callback_data.revision, state, action_id="disable"
    ):
        await _render_for_adv(query, adv, state)
        return
    await reset_draft(state, int(adv.id))
    await _abort_epoch_to_off(adv)
    await query.answer("A/B Hold выключен")
    adv = await _load_adv(callback_data.adv_setting_original_id)
    if adv is not None:
        await _render_for_adv(query, adv, state)
