"""CallbackData confirm-flow A/B Hold (§24, ux contract §§5–10).

Короткие UTF-8 префиксы укладываются в лимит Telegram 64 байта на
``callback_data``. Поля ``adv_setting_original_id``, ``step``, ``revision``,
``page`` обязательны для экранов S1+; на P1/P2/H1 в ``revision`` передаётся
``generation`` (§10).
"""

from __future__ import annotations

from enum import StrEnum

from aiogram.filters.callback_data import CallbackData


class ConfirmStep(StrEnum):
    """Короткие коды шага confirm-flow (поле ``step`` в callback_data)."""

    S1 = "s1"
    S1B = "1b"
    S2 = "s2"
    S3 = "s3"
    W3_PROPOSE = "w3"
    W3_CONFIRMED = "wc"
    A1 = "a1"
    A2 = "a2"
    P1 = "p1"
    P2 = "p2"
    H1 = "h1"
    SUMMARY = "sm"
    CANCEL = "cx"


class CahKeywordToggle(CallbackData, prefix="cah_k"):
    """``keyword_toggle`` — переключить включение ключа в черновике (S1/S1b)."""

    adv_setting_original_id: int
    step: str
    revision: int
    page: int
    keyword_idx: int


class CahPageNav(CallbackData, prefix="cah_pg"):
    """``page_prev`` / ``page_next`` — навигация по списку ключей."""

    adv_setting_original_id: int
    step: str
    revision: int
    page: int
    direction: str  # "p" | "n"


class CahKeywordSetConfirm(CallbackData, prefix="cah_kc"):
    """``keyword_set_confirm`` — зафиксировать набор ключей (S1/S1b)."""

    adv_setting_original_id: int
    step: str
    revision: int
    page: int = 0


class CahWarmupDurationPreset(CallbackData, prefix="cah_wp"):
    """``warmup_duration_preset`` — выбор длительности WARM_UP (S2)."""

    adv_setting_original_id: int
    step: str
    revision: int
    hours: int


class CahWarmupDurationConfirm(CallbackData, prefix="cah_wc"):
    """``warmup_duration_confirm`` — подтвердить длительность WARM_UP (S2)."""

    adv_setting_original_id: int
    step: str
    revision: int


class CahWarmupStatusRefresh(CallbackData, prefix="cah_wr"):
    """``warmup_status_refresh`` — обновить экран S3."""

    adv_setting_original_id: int
    step: str
    revision: int


class CahKeywordEditOpen(CallbackData, prefix="cah_ke"):
    """``keyword_edit_open`` — открыть S1b из S3."""

    adv_setting_original_id: int
    step: str
    revision: int


class CahTpConfirmAll(CallbackData, prefix="cah_tp"):
    """``tp_confirm_all`` — подтвердить все целевые позиции (W3-propose)."""

    adv_setting_original_id: int
    step: str
    revision: int
    page: int = 0


class CahContinueToAuto(CallbackData, prefix="cah_ca"):
    """``continue_to_auto`` — W3-confirmed → A1/A2 (§7)."""

    adv_setting_original_id: int
    step: str
    revision: int
    page: int = 0


class CahAutoParticipationConfirm(CallbackData, prefix="cah_ap"):
    """``auto_participation_confirm`` — участие Auto (A1)."""

    adv_setting_original_id: int
    step: str
    revision: int
    participates: int  # 0 | 1


class CahAutoBidEdit(CallbackData, prefix="cah_be"):
    """``auto_bid_edit`` — открыть ввод ставки Auto (A2)."""

    adv_setting_original_id: int
    step: str
    revision: int


class CahAutoBidConfirm(CallbackData, prefix="cah_bc"):
    """``auto_bid_confirm`` — подтвердить ставку Auto (A2)."""

    adv_setting_original_id: int
    step: str
    revision: int


class CahSyncStatusRefresh(CallbackData, prefix="cah_sr"):
    """``sync_status_refresh`` — обновить P1/P2."""

    adv_setting_original_id: int
    step: str
    revision: int


class CahConfirmBack(CallbackData, prefix="cah_bk"):
    """``back`` — назад с сохранением черновика (§7)."""

    adv_setting_original_id: int
    step: str
    revision: int
    page: int = 0


class CahCancelOpen(CallbackData, prefix="cah_co"):
    """``cancel_open`` — открыть диалог отмены (§8)."""

    adv_setting_original_id: int
    step: str
    revision: int
    page: int = 0


class CahCancelConfirmYes(CallbackData, prefix="cah_cy"):
    """``cancel_confirm_yes`` — подтвердить отмену."""

    adv_setting_original_id: int
    step: str
    revision: int
    page: int = 0


class CahCancelConfirmNo(CallbackData, prefix="cah_cn"):
    """``cancel_confirm_no`` — продолжить редактирование."""

    adv_setting_original_id: int
    step: str
    revision: int
    page: int = 0


class CahConfirmDisable(CallbackData, prefix="cah_ds"):
    """``disable`` (EXIT) — выключить A/B Hold."""

    adv_setting_original_id: int
    step: str
    revision: int


class CahOpenCurrentStep(CallbackData, prefix="cah_os"):
    """Кнопка «Открыть текущий шаг» (S0 menu или summary после Back).

    ``step`` обязателен в схеме CallbackData, но ``on_open_current_step`` его
    не читает — redraw идёт по ``card_ab_hold_phase`` (см. ``_render_for_adv``).
    """

    adv_setting_original_id: int
    step: str  # payload only; not used by on_open_current_step handler
    revision: int
