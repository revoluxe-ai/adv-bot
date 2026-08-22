"""Emergency kill switch для A/B Hold (change ``ab-hold-emergency-kill-switch``).

Owned write-path carve-out: pause intent + block-all keywords + durable latch
против top-up/restart. Не часть Hold §18 financial safety — см. decision
``ab-hold-emergency-kill-switch-write-path``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot import const as client_bot_const
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    normalize_card_ab_hold_mode,
)

logger = logging.getLogger(__name__)

SUPPORT_LINK = client_bot_const.SUPPORT_LINK

EmergencyApplyStatus = Literal["ok", "already_active", "partial"]


def is_ab_hold_emergency_visible(mode: CardAbHoldMode | str | None) -> bool:
    """Кнопка Emergency видна только при Hold mode ≠ OFF (spec visibility).

    Args:
        mode: сырой или нормализованный ``card_ab_hold_mode``.

    Returns:
        True если Emergency MUST быть доступен в UI.
    """
    return normalize_card_ab_hold_mode(mode) is not CardAbHoldMode.OFF


def is_ab_hold_emergency_latch_active(raw: bool | None) -> bool:
    """Нормализовать durable Emergency latch.

    Args:
        raw: значение PG ``card_ab_hold_emergency_latch``.

    Returns:
        True только при явном ``True`` (не truthy-mock / не произвольный object).
    """
    return raw is True


def should_suppress_budget_and_activity_restart(raw_latch: bool | None) -> bool:
    """Gate для auto-budget / activity-control (spec Emergency stops spend).

    Args:
        raw_latch: PG latch.

    Returns:
        True → MUST NOT top-up и MUST NOT рестартовать РК.
    """
    return is_ab_hold_emergency_latch_active(raw_latch)


@dataclass(frozen=True, slots=True)
class EmergencyApplyResult:
    """Итог owned Emergency executor (идемпотентность + честный partial).

    ``status``:
    - ``ok`` — latch + pause-intent + block-all без ошибки;
    - ``already_active`` — идемпотентный no-op;
    - ``partial`` — latch/pause-intent выставлены, но block-all упал
      (не silent success; UI MUST сказать честно).
    """

    latch_already_active: bool
    latch_set: bool
    keywords_blocked: int
    target_status_paused: bool
    status: EmergencyApplyStatus = "ok"
    block_error: str | None = None
    support_link: str = SUPPORT_LINK


def format_emergency_user_result_text(
    result: EmergencyApplyResult,
    *,
    campaign_label: str | None = None,
) -> str:
    """Пользовательский текст результата Emergency (без technical leak).

    Args:
        result: итог executor.
        campaign_label: опциональная метка РК (уже усечённая вызывающим).

    Returns:
        Текст для Telegram (≤4096 при разумном label).
    """
    if result.status == "already_active" or result.latch_already_active:
        return (
            "Аварийный стоп уже активен.\n"
            f"Поддержка: {result.support_link}"
        )
    label_line = f"Кампания: {campaign_label}\n" if campaign_label else ""
    if result.status == "partial":
        return (
            "🚨 Emergency частично выполнен.\n"
            f"{label_line}"
            "РК: пауза-intent и запрет пополнения включены, "
            "но блок ключей завершился с ошибкой.\n"
            "Hold режим не выключали.\n"
            "Напишите в поддержку — разберём.\n"
            f"Сразу напишите в поддержку: {result.support_link}"
        )
    return (
        "🚨 Emergency выполнен.\n"
        f"{label_line}"
        "РК: пауза-intent; ключи заблокированы; "
        f"бюджет не пополняется (заблокировано ключей: {result.keywords_blocked}).\n"
        "Hold режим не выключали.\n"
        "Если пришлось нажать — что-то сильно не так.\n"
        f"Сразу напишите в поддержку: {result.support_link}"
    )


async def apply_ab_hold_emergency_in_session(
    session: AsyncSession,
    *,
    adv_setting_id: int,
) -> EmergencyApplyResult:
    """Включить Emergency latch, пауза-intent target status, block-all keywords.

    Spec: Confirm executes kill switch / Emergency is idempotent.
    Decision carve-out: bulk ``hard_status=BLACK_LIST`` только здесь, не через
    ordinary freeze handlers.

    Hold mode MUST NOT сбрасываться в OFF.
    Latch + pause-intent ставятся ASAP; сбой block-all → ``status=partial``.

    Args:
        session: открытая AsyncSession (caller commits).
        adv_setting_id: PK ``AdvSetting.id``.

    Returns:
        ``EmergencyApplyResult`` с флагами идемпотентности и счётчиком ключей.
    """
    adv = await session.get(AdvSetting, adv_setting_id)
    if adv is None:
        raise ValueError(f"AdvSetting id={adv_setting_id} not found")

    if is_ab_hold_emergency_latch_active(
        getattr(adv, "card_ab_hold_emergency_latch", False)
    ):
        return EmergencyApplyResult(
            latch_already_active=True,
            latch_set=False,
            keywords_blocked=0,
            target_status_paused=False,
            status="already_active",
        )

    adv.card_ab_hold_emergency_latch = True
    # Intent для activity-control: не держать РК «должен быть запущен».
    # WB pause Search+Auto — через activity-control force-pause при latch
    # (task 3.2; прямой bot→WB pause optional follow-up).
    adv.auto_adv_target_status = False
    adv.auction_adv_target_status = False

    try:
        result = await session.execute(
            update(KeywordSetting)
            .where(KeywordSetting.adv_setting_id == adv_setting_id)
            .where(KeywordSetting.hard_status != client_bot_const.BLACK_LIST)
            .values(
                hard_status=client_bot_const.BLACK_LIST,
                # V3: BLACK_LIST (0) → strategy_mode OFF
                strategy_mode=KeywordStrategyMode.OFF,
            )
        )
        blocked = int(getattr(result, "rowcount", 0) or 0)
    except Exception as exc:
        logger.exception(
            "[adv_setting_id=%s] Emergency block-all failed after latch ON",
            adv_setting_id,
        )
        return EmergencyApplyResult(
            latch_already_active=False,
            latch_set=True,
            keywords_blocked=0,
            target_status_paused=True,
            status="partial",
            block_error=type(exc).__name__,
        )

    logger.warning(
        "[adv_setting_id=%s] A/B Hold Emergency latch ON; keywords_blocked=%s",
        adv_setting_id,
        blocked,
    )
    return EmergencyApplyResult(
        latch_already_active=False,
        latch_set=True,
        keywords_blocked=blocked,
        target_status_paused=True,
        status="ok",
    )


def mark_emergency_educated_in_memory(adv: AdvSetting) -> None:
    """Confirm/ACK образования на launch (spec Launch education).

    Args:
        adv: AdvSetting в сессии; поле ``card_ab_hold_emergency_educated``.
    """
    adv.card_ab_hold_emergency_educated = True


def is_emergency_educated(raw: bool | None) -> bool:
    """Проверка ACK образования Emergency.

    Args:
        raw: PG ``card_ab_hold_emergency_educated``.

    Returns:
        True только при явном ``True`` (PG bool SoT; Owner KEEP separate column).
    """
    return raw is True
