"""UI helpers paid-only A/B Hold (spec ``card-ab-hold-mode``)."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    normalize_card_ab_hold_mode,
)
from app.modules.shop_runner.service_manager.services.v3_status_mode_sync import (
    is_v3_campaign,
)


def is_card_ab_hold_ui_visible(adv_setting: AdvSetting) -> bool:
    """Показывать вход в A/B Hold только при paid bot_active.

    Spec: A/B Hold is paid-only — inactive bot hides entry.
    """
    return bool(adv_setting.bot_active)


def can_enable_card_ab_hold(adv_setting: AdvSetting) -> bool:
    """Разрешить enable A/B Hold только для paid-active кампании."""
    return bool(adv_setting.bot_active)


def can_enable_card_ab_hold_on_version(adv_setting: AdvSetting | object) -> bool:
    """A/B Hold — только при включённом боте (V3 runtime).

    Отдельный gate от ``can_enable_card_ab_hold`` сохранён для совместимости
    call-site'ов и отдельного UX-сообщения.
    """
    return is_v3_campaign(bool(getattr(adv_setting, "bot_active", False)))


def card_ab_hold_requires_v3_message() -> str:
    """Причина блокировки enable, когда бот выключен."""
    return (
        "A/B Hold доступен только при включённом боте. "
        "Включите бота для РК и повторите."
    )


def has_positive_plan_max_cpo(adv_setting: AdvSetting | object) -> bool:
    """True, если план max CPO задан и строго > 0 (decision §14a / spec).

    ENTER setup классифицирует ключи против плана ``max_price_for_order``; без
    положительного значения ``process_ab_setup`` детерминированно делает early
    return на каждом тике и никогда не доходит до ACTIVE, а кампания при этом уже
    исключена из ordinary automation — вечный semi-frozen PENDING_SETUP. Hard-gate
    на enable отсекает это до записи ``PENDING_SETUP`` (spec «Enable is blocked when
    plan max CPO is missing or non-positive»).
    """
    raw = getattr(adv_setting, "max_price_for_order", None)
    if raw is None:
        return False
    try:
        return float(raw) > 0
    except (TypeError, ValueError):
        return False


def card_ab_hold_requires_max_cpo_message() -> str:
    """Причина блокировки enable, когда план max CPO не задан / ≤ 0 (decision §14a).

    В пределах лимита ``answerCallbackQuery`` (≤200) — используется и как alert,
    и как текст экрана.
    """
    return (
        "Для A/B Hold нужен положительный план max CPO. "
        "Задайте план (макс. CPO) в настройках РК и повторите включение."
    )


def is_card_ab_hold_enable_noop(
    adv_setting: AdvSetting | object,
) -> bool:
    """True: Telegram Enable MUST no-op (уже PENDING_SETUP / ACTIVE).

    Spec ``Telegram Enable is idempotent`` / decision §10: не demote в
    PENDING, не Redis ENTER, не re-ENTER force sync. EXIT → OFF — перед
    новым ENTER.
    """
    mode = normalize_card_ab_hold_mode(
        getattr(adv_setting, "card_ab_hold_mode", None)
    )
    return mode in (CardAbHoldMode.PENDING_SETUP, CardAbHoldMode.ACTIVE)


def should_offer_card_ab_hold_enable_control(
    mode: CardAbHoldMode | str | None,
) -> bool:
    """True: показать кнопку Enable на экране A/B Hold.

    Decision §11: Enable MUST при ``OFF``; при PENDING/ACTIVE UI MAY
    скрыть Enable (Disable/Back остаются). Скрытие — сахар; §10 no-op
    остаётся safety net при stale callback.
    """
    return normalize_card_ab_hold_mode(mode) == CardAbHoldMode.OFF


def card_ab_hold_enable_noop_answer(adv_setting: AdvSetting | object) -> str:
    """Короткий callback answer при Enable no-op (лимит TG answerCallbackQuery)."""
    mode = normalize_card_ab_hold_mode(
        getattr(adv_setting, "card_ab_hold_mode", None)
    )
    if mode == CardAbHoldMode.ACTIVE:
        return "A/B Hold уже включён"
    if mode == CardAbHoldMode.PENDING_SETUP:
        return "Идёт подготовка A/B Hold…"
    return "A/B Hold уже в процессе"


def card_ab_hold_status_label(adv_setting: AdvSetting) -> str:
    """Текст статуса режима для кнопки меню.

    При ACTIVE + honest degradation (decision §8: enforcement не гарантирует чистый
    hold) label MUST NOT заявлять чистый «ВКЛ» — отражаем деградацию, чтобы UI не
    врал (spec scenario «Enforcement exceeding the WB minus cap degrades visibly»).
    """
    mode = normalize_card_ab_hold_mode(
        getattr(adv_setting, "card_ab_hold_mode", None)
    )
    if mode == CardAbHoldMode.ACTIVE:
        if bool(getattr(adv_setting, "card_ab_hold_degraded", False)):
            return "A/B Hold: ВКЛ (чистота не гарантируется)"
        return "A/B Hold: ВКЛ"
    if mode == CardAbHoldMode.PENDING_SETUP:
        return "A/B Hold: подготовка…"
    return "A/B Hold: выкл"
