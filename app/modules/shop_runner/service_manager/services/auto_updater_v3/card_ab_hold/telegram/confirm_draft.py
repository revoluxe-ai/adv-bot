"""FSM-черновики confirm-flow A/B Hold (ux contract §§7–10).

Spec requirements:
- «Back preserves the confirmation draft; Cancel is a separate explicit action»
- stale-callback detection через monotonic ``revision`` (pre-generation phases).

Данные хранятся в ``FSMContext`` под ключом ``card_ab_hold_confirm`` без
отдельного StatesGroup — по аналогии с другими экранами client bot.
"""

from __future__ import annotations

from typing import Any, cast

from aiogram.fsm.context import FSMContext

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_callbacks import (
    ConfirmStep,
)

_FSM_ROOT_KEY = "card_ab_hold_confirm"


def _adv_key(adv_setting_original_id: int) -> str:
    return str(int(adv_setting_original_id))


def _empty_draft() -> dict[str, Any]:
    return {
        "revision": 1,
        "page": 0,
        "return_step": ConfirmStep.S1.value,
        "keyword_included": {},
        "duration_hours": 24,
        "auto_participation": None,
        "auto_bid": None,
        "cancel_dialog_open": False,
        "summary_visible": False,
        "w3_confirmed_visible": False,
    }


async def load_draft(
    state: FSMContext,
    adv_setting_original_id: int,
) -> dict[str, Any]:
    """Загрузить черновик кампании; при отсутствии — инициализировать defaults."""
    data = await state.get_data()
    root = dict(data.get(_FSM_ROOT_KEY) or {})
    key = _adv_key(adv_setting_original_id)
    if key not in root:
        root[key] = _empty_draft()
        await state.update_data(**{_FSM_ROOT_KEY: root})
    return dict(root[key])


async def save_draft(
    state: FSMContext,
    adv_setting_original_id: int,
    draft: dict[str, Any],
) -> None:
    """Сохранить черновик кампании в FSM."""
    data = await state.get_data()
    root = dict(data.get(_FSM_ROOT_KEY) or {})
    root[_adv_key(adv_setting_original_id)] = dict(draft)
    await state.update_data(**{_FSM_ROOT_KEY: root})


async def get_revision(state: FSMContext, adv_setting_original_id: int) -> int:
    """Текущий revision черновика (§10)."""
    draft = await load_draft(state, adv_setting_original_id)
    return int(draft.get("revision") or 1)


async def bump_revision(state: FSMContext, adv_setting_original_id: int) -> int:
    """Увеличить revision и вернуть новое значение."""
    draft = await load_draft(state, adv_setting_original_id)
    new_rev = int(draft.get("revision") or 1) + 1
    draft["revision"] = new_rev
    await save_draft(state, adv_setting_original_id, draft)
    return new_rev


async def is_stale_revision(
    state: FSMContext,
    adv_setting_original_id: int,
    callback_revision: int,
) -> bool:
    """True, если callback revision не совпадает с актуальным (fail-closed §10)."""
    current = await get_revision(state, adv_setting_original_id)
    return int(callback_revision) != current


async def is_stale_generation(
    adv_generation: int | None,
    callback_revision: int,
) -> bool:
    """True, если callback generation (P1/P2/H1) устарел."""
    current = int(adv_generation or 0)
    return int(callback_revision) != current


async def set_page(
    state: FSMContext,
    adv_setting_original_id: int,
    page: int,
    *,
    bump: bool = True,
) -> dict[str, Any]:
    """Установить текущую страницу списка; опционально bump revision (§9)."""
    draft = await load_draft(state, adv_setting_original_id)
    draft["page"] = max(0, int(page))
    if bump:
        draft["revision"] = int(draft.get("revision") or 1) + 1
    await save_draft(state, adv_setting_original_id, draft)
    return draft


async def toggle_keyword_inclusion(
    state: FSMContext,
    adv_setting_original_id: int,
    keyword: str,
    *,
    default_included: bool = True,
) -> dict[str, Any]:
    """Переключить включение ключа в черновике S1/S1b."""
    draft = await load_draft(state, adv_setting_original_id)
    included_map: dict[str, bool] = dict(draft.get("keyword_included") or {})
    current = included_map.get(keyword, default_included)
    included_map[keyword] = not current
    draft["keyword_included"] = included_map
    draft["revision"] = int(draft.get("revision") or 1) + 1
    await save_draft(state, adv_setting_original_id, draft)
    return draft


def resolve_keyword_inclusion(
    draft: dict[str, Any],
    keyword: str,
    *,
    default_included: bool = True,
) -> bool:
    """Включён ли ключ в черновике."""
    included_map: dict[str, bool] = dict(draft.get("keyword_included") or {})
    return bool(included_map.get(keyword, default_included))


def selected_keywords(
    keywords: list[str],
    draft: dict[str, Any],
    *,
    default_included: bool = True,
) -> list[str]:
    """Список ключей, отмеченных для включения в тест."""
    return [
        kw
        for kw in keywords
        if resolve_keyword_inclusion(draft, kw, default_included=default_included)
    ]


async def mark_summary_visible(
    state: FSMContext,
    adv_setting_original_id: int,
    return_step: ConfirmStep | str,
) -> dict[str, Any]:
    """Back: сохранить черновик и показать summary (§7)."""
    draft = await load_draft(state, adv_setting_original_id)
    draft["summary_visible"] = True
    draft["return_step"] = str(return_step)
    draft["cancel_dialog_open"] = False
    draft["revision"] = int(draft.get("revision") or 1) + 1
    await save_draft(state, adv_setting_original_id, draft)
    return draft


async def clear_summary(
    state: FSMContext,
    adv_setting_original_id: int,
) -> dict[str, Any]:
    """Скрыть summary и вернуться к редактированию шага."""
    draft = await load_draft(state, adv_setting_original_id)
    draft["summary_visible"] = False
    draft["cancel_dialog_open"] = False
    draft["revision"] = int(draft.get("revision") or 1) + 1
    await save_draft(state, adv_setting_original_id, draft)
    return draft


async def open_cancel_dialog(
    state: FSMContext,
    adv_setting_original_id: int,
) -> dict[str, Any]:
    """Открыть поддиалог Cancel (§8)."""
    draft = await load_draft(state, adv_setting_original_id)
    draft["cancel_dialog_open"] = True
    await save_draft(state, adv_setting_original_id, draft)
    return draft


async def close_cancel_dialog(
    state: FSMContext,
    adv_setting_original_id: int,
) -> dict[str, Any]:
    """Закрыть поддиалог Cancel без изменения черновика."""
    draft = await load_draft(state, adv_setting_original_id)
    draft["cancel_dialog_open"] = False
    await save_draft(state, adv_setting_original_id, draft)
    return draft


async def reset_draft(
    state: FSMContext,
    adv_setting_original_id: int,
) -> None:
    """Сбросить черновик кампании (abort epoch attempt)."""
    data = await state.get_data()
    root = dict(data.get(_FSM_ROOT_KEY) or {})
    root[_adv_key(adv_setting_original_id)] = _empty_draft()
    await state.update_data(**{_FSM_ROOT_KEY: root})


def is_w3_confirmed_visible(draft: dict[str, Any]) -> bool:
    """True, если UX-экран W3-confirmed (read-only) должен отображаться (§7)."""
    return bool(draft.get("w3_confirmed_visible"))


def should_show_w3_confirmed_read_only(adv: Any, draft: dict[str, Any]) -> bool:
    """W3-confirmed UX: FSM-флаг или durable TP после restart (§7 / OP-014 blocker 1).

    Если FSM потерян, но в PG есть ``confirmed_target_places`` и phase ожидает
    Auto-confirm — показываем read-only W3, не editable W3-propose.
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
        CardAbHoldPhase,
        normalize_card_ab_hold_phase,
    )

    if is_w3_confirmed_visible(draft):
        return True
    phase = normalize_card_ab_hold_phase(getattr(adv, "card_ab_hold_phase", None))
    if phase not in (
        CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM,
        CardAbHoldPhase.AWAITING_AUTO_BID_CONFIRM,
    ):
        return False
    tp_map = cast(
        dict[str, Any],
        getattr(adv, "card_ab_hold_confirmed_target_places_json", None) or {},
    )
    return bool(tp_map)


async def set_w3_confirmed_visible(
    state: FSMContext,
    adv_setting_original_id: int,
    visible: bool,
) -> dict[str, Any]:
    """Показать/скрыть W3-confirmed между TP confirm и A1 (§7)."""
    draft = await load_draft(state, adv_setting_original_id)
    draft["w3_confirmed_visible"] = bool(visible)
    await save_draft(state, adv_setting_original_id, draft)
    return draft


async def discard_edit_draft_only(
    state: FSMContext,
    adv_setting_original_id: int,
) -> None:
    """S1b cancel: сбросить только edit-draft, durable keywords не трогаем (§8)."""
    draft = await load_draft(state, adv_setting_original_id)
    draft["keyword_included"] = {}
    draft["page"] = 0
    draft["cancel_dialog_open"] = False
    draft["summary_visible"] = False
    draft["return_step"] = ConfirmStep.S3.value
    draft["revision"] = int(draft.get("revision") or 1) + 1
    await save_draft(state, adv_setting_original_id, draft)
