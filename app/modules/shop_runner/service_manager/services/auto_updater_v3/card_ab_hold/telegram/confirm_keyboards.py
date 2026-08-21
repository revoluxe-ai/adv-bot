"""Клавиатуры confirm-flow A/B Hold (ux contract §5).

Экраны S1/S1b/S2/S3/W3/A1/A2/P1/P2 — exhaustive row sets per contract.
S3 включает «Изменить набор ключей» → ``keyword_edit_open`` (§24.6).
"""

from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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
    resolve_keyword_inclusion,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_pagination import (
    paginate,
)


def _nav_row(
    *,
    adv_id: int,
    step: ConfirmStep | str,
    revision: int,
    page: int,
    total_pages: int,
) -> list[InlineKeyboardButton] | None:
    """Строка пагинации «◀ Стр.» / «Стр. ▶» только при >1 странице (§9)."""
    if total_pages <= 1:
        return None
    step_str = str(step)
    buttons: list[InlineKeyboardButton] = []
    if page > 0:
        buttons.append(
            InlineKeyboardButton(
                text="◀ Стр.",
                callback_data=CahPageNav(
                    adv_setting_original_id=adv_id,
                    step=step_str,
                    revision=revision,
                    page=page,
                    direction="p",
                ).pack(),
            )
        )
    if page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton(
                text="Стр. ▶",
                callback_data=CahPageNav(
                    adv_setting_original_id=adv_id,
                    step=step_str,
                    revision=revision,
                    page=page,
                    direction="n",
                ).pack(),
            )
        )
    return buttons or None


def _back_cancel_row(
    *,
    adv_id: int,
    step: ConfirmStep | str,
    revision: int,
    page: int = 0,
) -> list[InlineKeyboardButton]:
    """«← Назад» и «Отмена» — разные callback (§8)."""
    step_str = str(step)
    return [
        InlineKeyboardButton(
            text="← Назад",
            callback_data=CahConfirmBack(
                adv_setting_original_id=adv_id,
                step=step_str,
                revision=revision,
                page=page,
            ).pack(),
        ),
        InlineKeyboardButton(
            text="Отмена",
            callback_data=CahCancelOpen(
                adv_setting_original_id=adv_id,
                step=step_str,
                revision=revision,
                page=page,
            ).pack(),
        ),
    ]


def build_cancel_dialog_keyboard(
    *,
    adv_id: int,
    step: ConfirmStep | str,
    revision: int,
    page: int = 0,
) -> InlineKeyboardMarkup:
    """Поддиалог Cancel: «Да, отменить» / «Нет, продолжить»."""
    step_str = str(step)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, отменить",
                    callback_data=CahCancelConfirmYes(
                        adv_setting_original_id=adv_id,
                        step=step_str,
                        revision=revision,
                        page=page,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="Нет, продолжить",
                    callback_data=CahCancelConfirmNo(
                        adv_setting_original_id=adv_id,
                        step=step_str,
                        revision=revision,
                        page=page,
                    ).pack(),
                ),
            ]
        ]
    )


def build_summary_keyboard(
    *,
    adv_id: int,
    return_step: ConfirmStep | str,
    revision: int,
) -> InlineKeyboardMarkup:
    """Summary после Back (§7)."""
    step_str = str(return_step)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть текущий шаг",
                    callback_data=CahOpenCurrentStep(
                        adv_setting_original_id=adv_id,
                        step=step_str,
                        revision=revision,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data=CahConfirmBack(
                        adv_setting_original_id=adv_id,
                        step=ConfirmStep.SUMMARY.value,
                        revision=revision,
                    ).pack(),
                )
            ],
        ]
    )


def build_s1_keyboard(
    *,
    adv_id: int,
    all_keywords: list[str],
    draft: dict[str, Any],
    revision: int,
    page: int,
    is_s1b: bool = False,
) -> InlineKeyboardMarkup:
    """S1 / S1b — keyword confirm (contract §5)."""
    step = ConfirmStep.S1B if is_s1b else ConfirmStep.S1
    page_items, norm_page, total_pages = paginate(all_keywords, page)
    rows: list[list[InlineKeyboardButton]] = []
    for idx, kw in enumerate(page_items):
        global_idx = norm_page * 10 + idx
        included = resolve_keyword_inclusion(draft, kw, default_included=True)
        mark = "✓" if included else "✗"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {kw}",
                    callback_data=CahKeywordToggle(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                        page=norm_page,
                        keyword_idx=global_idx,
                    ).pack(),
                )
            ]
        )
    nav = _nav_row(
        adv_id=adv_id,
        step=step,
        revision=revision,
        page=norm_page,
        total_pages=total_pages,
    )
    if nav:
        rows.append(nav)
    rows.append(
        [
            InlineKeyboardButton(
                text="Подтвердить набор",
                callback_data=CahKeywordSetConfirm(
                    adv_setting_original_id=adv_id,
                    step=step.value,
                    revision=revision,
                    page=norm_page,
                ).pack(),
            )
        ]
    )
    rows.append(
        _back_cancel_row(
            adv_id=adv_id, step=step, revision=revision, page=norm_page
        )
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_s2_keyboard(
    *,
    adv_id: int,
    revision: int,
) -> InlineKeyboardMarkup:
    """S2 — WARM_UP duration config."""
    step = ConfirmStep.S2
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="24ч (по умолчанию)",
                    callback_data=CahWarmupDurationPreset(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                        hours=24,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Увеличить: +24ч",
                    callback_data=CahWarmupDurationPreset(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                        hours=48,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="Увеличить: +48ч",
                    callback_data=CahWarmupDurationPreset(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                        hours=72,
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Подтвердить длительность",
                    callback_data=CahWarmupDurationConfirm(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                    ).pack(),
                )
            ],
            _back_cancel_row(adv_id=adv_id, step=step, revision=revision),
        ]
    )


def build_s3_keyboard(
    *,
    adv_id: int,
    revision: int,
) -> InlineKeyboardMarkup:
    """S3 — WARM_UP progress; includes keyword_edit_open (§24.6)."""
    step = ConfirmStep.S3
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Обновить статус",
                    callback_data=CahWarmupStatusRefresh(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Изменить набор ключей",
                    callback_data=CahKeywordEditOpen(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Выключить A/B тест",
                    callback_data=CahConfirmDisable(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data=CahConfirmBack(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                    ).pack(),
                )
            ],
        ]
    )


def build_w3_propose_keyboard(
    *,
    adv_id: int,
    rows: list[tuple[str, int, int]],
    revision: int,
    page: int,
) -> InlineKeyboardMarkup:
    """W3-propose — display-only TP rows + confirm."""
    step = ConfirmStep.W3_PROPOSE
    page_items, norm_page, total_pages = paginate(rows, page)
    kb_rows: list[list[InlineKeyboardButton]] = []
    for keyword, fact, target in page_items:
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text=f"{keyword}: факт {fact} → цель {target}",
                    callback_data=CahConfirmBack(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                        page=norm_page,
                    ).pack(),
                )
            ]
        )
    nav = _nav_row(
        adv_id=adv_id,
        step=step,
        revision=revision,
        page=norm_page,
        total_pages=total_pages,
    )
    if nav:
        kb_rows.append(nav)
    if rows:
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text="Подтвердить целевые позиции",
                    callback_data=CahTpConfirmAll(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                        page=norm_page,
                    ).pack(),
                )
            ]
        )
    kb_rows.append(
        _back_cancel_row(
            adv_id=adv_id, step=step, revision=revision, page=norm_page
        )
    )
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


def build_w3_confirmed_keyboard(
    *,
    adv_id: int,
    rows: list[tuple[str, int, int]],
    revision: int,
    page: int,
) -> InlineKeyboardMarkup:
    """W3-confirmed — read-only."""
    step = ConfirmStep.W3_CONFIRMED
    page_items, norm_page, total_pages = paginate(rows, page)
    kb_rows: list[list[InlineKeyboardButton]] = []
    for keyword, fact, target in page_items:
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text=f"{keyword}: факт {fact} → цель {target} (зафиксировано)",
                    callback_data=CahConfirmBack(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                        page=norm_page,
                    ).pack(),
                )
            ]
        )
    nav = _nav_row(
        adv_id=adv_id,
        step=step,
        revision=revision,
        page=norm_page,
        total_pages=total_pages,
    )
    if nav:
        kb_rows.append(nav)
    kb_rows.append(
        [
            InlineKeyboardButton(
                text="Продолжить →",
                callback_data=CahContinueToAuto(
                    adv_setting_original_id=adv_id,
                    step=step.value,
                    revision=revision,
                    page=norm_page,
                ).pack(),
            )
        ]
    )
    kb_rows.append(
        [
            InlineKeyboardButton(
                text="Выключить A/B тест",
                callback_data=CahConfirmDisable(
                    adv_setting_original_id=adv_id,
                    step=step.value,
                    revision=revision,
                ).pack(),
            )
        ]
    )
    kb_rows.append(
        [
            InlineKeyboardButton(
                text="← Назад",
                callback_data=CahConfirmBack(
                    adv_setting_original_id=adv_id,
                    step=step.value,
                    revision=revision,
                    page=norm_page,
                ).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


def build_a1_keyboard(
    *,
    adv_id: int,
    revision: int,
) -> InlineKeyboardMarkup:
    """A1 — Auto participation."""
    step = ConfirmStep.A1
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, участвует",
                    callback_data=CahAutoParticipationConfirm(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                        participates=1,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="Нет, не участвует",
                    callback_data=CahAutoParticipationConfirm(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                        participates=0,
                    ).pack(),
                ),
            ],
            _back_cancel_row(adv_id=adv_id, step=step, revision=revision),
        ]
    )


def build_a2_keyboard(
    *,
    adv_id: int,
    revision: int,
    auto_bid: float,
) -> InlineKeyboardMarkup:
    """A2 — Auto bid confirm."""
    step = ConfirmStep.A2
    bid_text = f"{auto_bid:.0f}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Подтвердить ставку Auto: {bid_text} ₽",
                    callback_data=CahAutoBidConfirm(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Изменить значение",
                    callback_data=CahAutoBidEdit(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=revision,
                    ).pack(),
                )
            ],
            _back_cancel_row(adv_id=adv_id, step=step, revision=revision),
        ]
    )


def build_p1_keyboard(
    *,
    adv_id: int,
    generation: int,
) -> InlineKeyboardMarkup:
    """P1 — syncing (no Disable on first sync in flight)."""
    step = ConfirmStep.P1
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Обновить статус",
                    callback_data=CahSyncStatusRefresh(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=generation,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data=CahConfirmBack(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=generation,
                    ).pack(),
                )
            ],
        ]
    )


def build_p2_keyboard(
    *,
    adv_id: int,
    generation: int,
) -> InlineKeyboardMarkup:
    """P2 — partial sync."""
    step = ConfirmStep.P2
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Обновить статус",
                    callback_data=CahSyncStatusRefresh(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=generation,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Выключить A/B тест",
                    callback_data=CahConfirmDisable(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=generation,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data=CahConfirmBack(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=generation,
                    ).pack(),
                )
            ],
        ]
    )


def build_h1_keyboard(
    *,
    adv_id: int,
    generation: int,
) -> InlineKeyboardMarkup:
    """H1 — active hold (read-only status)."""
    step = ConfirmStep.H1
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Подробности по ключам",
                    callback_data=CahConfirmBack(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=generation,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Выключить A/B тест",
                    callback_data=CahConfirmDisable(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=generation,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data=CahConfirmBack(
                        adv_setting_original_id=adv_id,
                        step=step.value,
                        revision=generation,
                    ).pack(),
                )
            ],
        ]
    )
