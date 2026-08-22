"""Async PG write-path epoch lifecycle A/B Hold (§19–§22).

Owner: A/B Hold epoch/setup write-path (decision ``ab-hold-epoch-lifecycle-and-generation-ownership``).
Telegram-хендлеры только инициируют переходы; generation/intent пишутся здесь с ``FOR UPDATE``.

Session seam: parent orchestration открывает ``sm(read_only=False)`` и передаёт
``AsyncSession`` в ``*_in_session`` child, где выполняется store-работа.
"""

from __future__ import annotations

import datetime
import logging
import math
from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    DEFAULT_WARMUP_HOURS,
    CardAbHoldSyncStatus,
    all_confirms_complete,
    build_pending_intent_payload,
    build_wb_sync_idempotency_key,
    clamp_warmup_duration_hours,
    clear_epoch_fields_values,
    normalize_card_ab_hold_sync_status,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.feature_flag import (
    can_enter_epoch_managed_ab_hold,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
    normalize_card_ab_hold_phase,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


def _select_adv_for_update(adv_setting_id: int):
    """SELECT AdvSetting FOR UPDATE без joined ``wb_cabinet`` (иначе PG rejects FOR UPDATE)."""
    return (
        select(AdvSetting)
        .options(noload(AdvSetting.wb_cabinet))
        .where(AdvSetting.id == adv_setting_id)
        .with_for_update()
    )


class EpochWriteError(ValueError):
    """Недопустимый переход epoch write-path."""


def _validated_confirmed_keyword_subset(
    adv: AdvSetting,
    tp_map: Mapping[Any, object],
) -> list[str]:
    """Проверить durable TP payload и вернуть оставшийся keyword-set.

    Args:
        adv: строка ``AdvSetting`` после ``SELECT ... FOR UPDATE``.
        tp_map: proposed/confirmed target places от Telegram flow.

    Returns:
        Подмножество исходного confirmed keyword-set в его исходном порядке.

    Raises:
        EpochWriteError: если payload пуст, содержит невалидную цель или
            ключ вне текущего confirmed keyword-set.
    """
    if not tp_map:
        raise EpochWriteError("confirm_target_places requires a non-empty tp_map")

    current_keywords = list(
        getattr(adv, "card_ab_hold_confirmed_keywords_json", None) or []
    )
    current_keyword_set = set(current_keywords)
    payload_keys = set(tp_map)
    if not payload_keys.issubset(current_keyword_set):
        raise EpochWriteError(
            "confirm_target_places payload contains a keyword outside "
            "the confirmed keyword-set"
        )
    for keyword, target_place in tp_map.items():
        if not isinstance(keyword, str) or not keyword:
            raise EpochWriteError("confirm_target_places keyword must be non-empty text")
        if isinstance(target_place, bool) or not isinstance(target_place, int):
            raise EpochWriteError(
                "confirm_target_places target place must be an integer"
            )
        if target_place <= 0:
            raise EpochWriteError(
                "confirm_target_places target place must be positive"
            )
    return [keyword for keyword in current_keywords if keyword in payload_keys]


async def start_epoch_on_enable_in_session(
    session: AsyncSession,
    adv_setting_id: int,
    *,
    epoch_managed: bool,
) -> None:
    """Записать ENTER mode/phase в переданной PG session (FOR UPDATE).

    Args:
        session: injectable async session (WRITE).
        adv_setting_id: ``AdvSetting.id``.
        epoch_managed: True → phase ``AWAITING_KEYWORD_CONFIRM``; иначе NULL.
    """
    stmt = _select_adv_for_update(adv_setting_id)
    _ = (await session.execute(stmt)).scalar_one()
    values: dict[str, Any] = {
        "card_ab_hold_mode": CardAbHoldMode.PENDING_SETUP.value,
    }
    if epoch_managed:
        values["card_ab_hold_phase"] = (
            CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM.value
        )
    else:
        values["card_ab_hold_phase"] = None
    stmt_up = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_id)
        .values(**values)
    )
    _ = await session.execute(stmt_up)
    await session.commit()


async def start_epoch_on_enable(
    adv_setting_id: int,
    *,
    adv_id: int,
    shop_id: int | None = None,
) -> bool:
    """Инициализировать epoch-managed flow при ENTER (§19 / §25 flag).

    Если ``can_enter_epoch_managed_ab_hold`` — mode ``PENDING_SETUP`` +
    phase ``AWAITING_KEYWORD_CONFIRM``; иначе phase остаётся NULL (legacy MVP-1).

    Returns:
        True, если кампания переведена на epoch-managed flow.
    """
    epoch_managed = can_enter_epoch_managed_ab_hold(adv_id=int(adv_id), shop_id=shop_id)
    async with sm(read_only=False) as session:
        await start_epoch_on_enable_in_session(
            session, adv_setting_id, epoch_managed=epoch_managed
        )
    logger.info(
        "[adv_setting_id=%s adv_id=%s] start_epoch_on_enable epoch_managed=%s",
        adv_setting_id,
        adv_id,
        epoch_managed,
    )
    return epoch_managed


async def confirm_keyword_set_and_start_warmup_in_session(
    session: AsyncSession,
    adv_setting_id: int,
    keywords: list[str],
    *,
    duration_hours: int = DEFAULT_WARMUP_HOURS,
) -> bool:
    """Durable keyword-set + WARM_UP phase в переданной session.

    Returns:
        True, если сброшен running WARM_UP timer после смены keyword-set (S1b).
    """
    clamped = clamp_warmup_duration_hours(duration_hours)
    normalized_keywords = list(keywords)
    stmt = _select_adv_for_update(adv_setting_id)
    adv = (await session.execute(stmt)).scalar_one()
    prev_keywords = cast(
        list[str],
        getattr(adv, "card_ab_hold_confirmed_keywords_json", None) or [],
    )
    prev_phase = normalize_card_ab_hold_phase(
        getattr(adv, "card_ab_hold_phase", None)
    )
    cleared_running_timer = (
        prev_phase == CardAbHoldPhase.WARM_UP
        and getattr(adv, "card_ab_hold_warmup_started_at", None) is not None
        and list(prev_keywords) != normalized_keywords
    )
    stmt_up = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_id)
        .values(
            card_ab_hold_confirmed_keywords_json=normalized_keywords,
            card_ab_hold_phase=CardAbHoldPhase.WARM_UP.value,
            card_ab_hold_warmup_started_at=None,
            card_ab_hold_warmup_duration_hours=clamped,
        )
    )
    _ = await session.execute(stmt_up)
    await session.commit()
    return cleared_running_timer


async def confirm_keyword_set_and_start_warmup(
    adv_setting_id: int,
    keywords: list[str],
    *,
    duration_hours: int = DEFAULT_WARMUP_HOURS,
) -> None:
    """Подтвердить набор ключей и войти в WARM_UP duration-configuration (§19 / WARMS2).

    S1 (первый confirm) и S1b (edit во время running WARM_UP): durable keyword-set
    + phase ``WARM_UP``, ``warmup_started_at`` MUST оставаться/становиться NULL.
    Таймер стартует только в ``set_warmup_duration`` после duration confirm (S2→S3).
    Decision: ``ab-hold-epoch-lifecycle-and-generation-ownership`` §1/§4.
    """
    async with sm(read_only=False) as session:
        cleared_running_timer = await confirm_keyword_set_and_start_warmup_in_session(
            session,
            adv_setting_id,
            keywords,
            duration_hours=duration_hours,
        )
    if cleared_running_timer:
        logger.info(
            "[adv_setting_id=%s] WARM_UP timer cleared after keyword-set change; "
            "awaiting duration confirm (S2)",
            adv_setting_id,
        )


async def set_warmup_duration_in_session(
    session: AsyncSession,
    adv_setting_id: int,
    hours: int,
) -> int:
    """Persist clamped WARM_UP hours + ``warmup_started_at=now`` в session.

    Returns:
        Применённая (clamped) длительность в часах.
    """
    clamped = clamp_warmup_duration_hours(hours)
    now = datetime.datetime.now(datetime.timezone.utc)
    stmt = _select_adv_for_update(adv_setting_id)
    _ = (await session.execute(stmt)).scalar_one()
    stmt_up = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_id)
        .values(
            card_ab_hold_warmup_duration_hours=clamped,
            card_ab_hold_warmup_started_at=now,
        )
    )
    _ = await session.execute(stmt_up)
    await session.commit()
    return clamped


async def set_warmup_duration(adv_setting_id: int, hours: int) -> int:
    """Подтвердить длительность WARM_UP и стартовать таймер (§19 / WARMS2 S2→S3).

    Persist'ит clamped hours и выставляет ``warmup_started_at=now`` (единственный
    write-moment старта/рестарта таймера после keyword confirm / S1b clear).
    Decision: ``ab-hold-epoch-lifecycle-and-generation-ownership`` §1.

    Returns:
        Применённая (clamped) длительность в часах.
    """
    async with sm(read_only=False) as session:
        clamped = await set_warmup_duration_in_session(session, adv_setting_id, hours)
    logger.info(
        "[adv_setting_id=%s] WARM_UP timer started duration_hours=%s",
        adv_setting_id,
        clamped,
    )
    return clamped


async def advance_warmup_to_tp_confirm_in_session(
    session: AsyncSession,
    adv_setting_id: int,
) -> bool:
    """WARM_UP → AWAITING_TP_CONFIRM в переданной session.

    Returns:
        True, если переход выполнен; False, если phase уже не ``WARM_UP``.
    """
    stmt = _select_adv_for_update(adv_setting_id)
    adv = (await session.execute(stmt)).scalar_one()
    phase = normalize_card_ab_hold_phase(getattr(adv, "card_ab_hold_phase", None))
    if phase != CardAbHoldPhase.WARM_UP:
        logger.info(
            "[adv_setting_id=%s] advance_warmup_to_tp_confirm skipped: phase=%s",
            adv_setting_id,
            phase,
        )
        return False
    stmt_up = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_id)
        .values(card_ab_hold_phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value)
    )
    _ = await session.execute(stmt_up)
    await session.commit()
    return True


async def advance_warmup_to_tp_confirm(adv_setting_id: int) -> bool:
    """Перевести epoch из WARM_UP в AWAITING_TP_CONFIRM после истечения таймера (§19).

    Owner: ``ab-hold-epoch-lifecycle-and-generation-ownership``. Не пишет TP —
    только смена phase (FOR UPDATE).

    Returns:
        True, если переход выполнен; False, если phase уже не ``WARM_UP``.
    """
    async with sm(read_only=False) as session:
        advanced = await advance_warmup_to_tp_confirm_in_session(
            session, adv_setting_id
        )
    if advanced:
        logger.info(
            "[adv_setting_id=%s] WARM_UP elapsed → AWAITING_TP_CONFIRM",
            adv_setting_id,
        )
    return advanced


async def confirm_target_places_in_session(
    session: AsyncSession,
    adv_setting_id: int,
    tp_map: Mapping[str, object],
) -> None:
    """Durable confirmed TP + phase advance в переданной session.

    Raises:
        EpochWriteError: если текущая phase не ``AWAITING_TP_CONFIRM``.
    """
    stmt = _select_adv_for_update(adv_setting_id)
    adv = (await session.execute(stmt)).scalar_one()
    phase = normalize_card_ab_hold_phase(getattr(adv, "card_ab_hold_phase", None))
    if phase != CardAbHoldPhase.AWAITING_TP_CONFIRM:
        raise EpochWriteError(
            f"confirm_target_places requires AWAITING_TP_CONFIRM, got {phase}"
        )
    confirmed_keywords = _validated_confirmed_keyword_subset(adv, tp_map)
    stmt_up = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_id)
        .values(
            card_ab_hold_confirmed_keywords_json=confirmed_keywords,
            card_ab_hold_confirmed_target_places_json=dict(tp_map),
            card_ab_hold_phase=(
                CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM.value
            ),
        )
    )
    _ = await session.execute(stmt_up)
    await session.commit()


async def confirm_target_places(
    adv_setting_id: int,
    tp_map: Mapping[str, object],
) -> None:
    """Durable confirmed TP; phase → ``AWAITING_AUTO_PARTICIPATION_CONFIRM`` (§20).

    Raises:
        EpochWriteError: если текущая phase не ``AWAITING_TP_CONFIRM``.
    """
    async with sm(read_only=False) as session:
        await confirm_target_places_in_session(session, adv_setting_id, tp_map)


async def confirm_auto_participation_in_session(
    session: AsyncSession,
    adv_setting_id: int,
    value: bool,
) -> None:
    """Подтвердить участие Auto в переданной session → AWAITING_AUTO_BID_CONFIRM."""
    stmt = _select_adv_for_update(adv_setting_id)
    adv = (await session.execute(stmt)).scalar_one()
    phase = normalize_card_ab_hold_phase(getattr(adv, "card_ab_hold_phase", None))
    if phase != CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM:
        raise EpochWriteError(
            "confirm_auto_participation requires "
            "AWAITING_AUTO_PARTICIPATION_CONFIRM"
        )
    stmt_up = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_id)
        .values(
            card_ab_hold_confirmed_auto_participation=bool(value),
            card_ab_hold_phase=CardAbHoldPhase.AWAITING_AUTO_BID_CONFIRM.value,
        )
    )
    _ = await session.execute(stmt_up)
    await session.commit()


async def confirm_auto_participation(adv_setting_id: int, value: bool) -> None:
    """Подтвердить участие Auto → phase ``AWAITING_AUTO_BID_CONFIRM`` (§21)."""
    async with sm(read_only=False) as session:
        await confirm_auto_participation_in_session(session, adv_setting_id, value)


async def confirm_auto_bid_in_session(
    session: AsyncSession,
    adv_setting_id: int,
    bid: float,
) -> int:
    """Persist confirmed auto bid в session; вернуть ``adv_id`` для intent.

    Raises:
        EpochWriteError: если phase не ``AWAITING_AUTO_BID_CONFIRM``.
    """
    if not math.isfinite(bid):
        raise EpochWriteError("confirm_auto_bid bid must be finite")
    stmt = _select_adv_for_update(adv_setting_id)
    adv = (await session.execute(stmt)).scalar_one()
    adv_id = int(adv.adv_id)
    phase = normalize_card_ab_hold_phase(getattr(adv, "card_ab_hold_phase", None))
    if phase != CardAbHoldPhase.AWAITING_AUTO_BID_CONFIRM:
        raise EpochWriteError(
            "confirm_auto_bid requires AWAITING_AUTO_BID_CONFIRM"
        )
    stmt_up = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_id)
        .values(card_ab_hold_confirmed_auto_bid=float(bid))
    )
    _ = await session.execute(stmt_up)
    await session.commit()
    return adv_id


async def confirm_auto_bid(adv_setting_id: int, bid: float) -> bool:
    """Подтвердить ставку Auto и создать durable PENDING intent (§21 / §22).

    Returns:
        True, если intent создан; False, если duplicate idempotency (no-op).
    """
    async with sm(read_only=False) as session:
        adv_id = await confirm_auto_bid_in_session(session, adv_setting_id, bid)

    return await create_pending_intent_for_generation(
        adv_setting_id,
        adv_id=adv_id,
    )


async def create_pending_intent_for_generation_in_session(
    session: AsyncSession,
    adv_setting_id: int,
    *,
    adv_id: int,
) -> bool:
    """SELECT FOR UPDATE; bump generation; intent + idempotency + PENDING.

    Returns:
        True, если intent записан; False при duplicate no-op.
    """
    stmt = _select_adv_for_update(adv_setting_id)
    adv = (await session.execute(stmt)).scalar_one()
    if not all_confirms_complete(adv):
        raise EpochWriteError(
            "create_pending_intent_for_generation: confirms incomplete"
        )

    if getattr(adv, "card_ab_hold_pending_intent_json", None) is not None:
        logger.info(
            "[adv_setting_id=%s] pending intent already present — no-op",
            adv_setting_id,
        )
        return False

    current_gen = int(getattr(adv, "card_ab_hold_generation", 0) or 0)
    next_gen = current_gen + 1
    idem_key = build_wb_sync_idempotency_key(adv_id, next_gen)
    existing_key = getattr(adv, "card_ab_hold_wb_sync_idempotency_key", None)
    if existing_key == idem_key:
        logger.info(
            "[adv_setting_id=%s] duplicate intent idempotency key=%s no-op",
            adv_setting_id,
            idem_key,
        )
        return False

    keywords = cast(
        list[str],
        getattr(adv, "card_ab_hold_confirmed_keywords_json", None) or [],
    )
    target_places = cast(
        dict[str, int],
        getattr(adv, "card_ab_hold_confirmed_target_places_json", None) or {},
    )
    auto_participation = bool(adv.card_ab_hold_confirmed_auto_participation)
    auto_bid = float(adv.card_ab_hold_confirmed_auto_bid or 0)
    payload = build_pending_intent_payload(
        generation=next_gen,
        keywords=keywords,
        target_places=target_places,
        auto_participation=auto_participation,
        auto_bid=auto_bid,
    )
    stmt_up = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_id)
        .values(
            card_ab_hold_generation=next_gen,
            card_ab_hold_pending_intent_json=payload,
            card_ab_hold_wb_sync_idempotency_key=idem_key,
            card_ab_hold_phase=CardAbHoldPhase.PENDING_INTENT.value,
            card_ab_hold_sync_status=CardAbHoldSyncStatus.PENDING.value,
        )
    )
    _ = await session.execute(stmt_up)
    await session.commit()
    logger.info(
        "[adv_setting_id=%s adv_id=%s] PENDING intent generation=%s key=%s",
        adv_setting_id,
        adv_id,
        next_gen,
        idem_key,
    )
    return True


async def create_pending_intent_for_generation(
    adv_setting_id: int,
    *,
    adv_id: int,
) -> bool:
    """SELECT FOR UPDATE; bump generation; intent + idempotency + PENDING (§22.5).

    Duplicate idempotency key для той же generation → no-op, generation не bump'ится.

    Returns:
        True, если intent записан; False при duplicate no-op.
    """
    async with sm(read_only=False) as session:
        return await create_pending_intent_for_generation_in_session(
            session, adv_setting_id, adv_id=adv_id
        )


async def mark_wb_sync_status_in_session(
    session: AsyncSession,
    adv_setting_id: int,
    status: CardAbHoldSyncStatus | str,
) -> None:
    """Обновить sync_status (+ WB_SYNC phase) в переданной session."""
    normalized = normalize_card_ab_hold_sync_status(status)
    if normalized not in (
        CardAbHoldSyncStatus.PENDING,
        CardAbHoldSyncStatus.PARTIAL,
        CardAbHoldSyncStatus.COMPLETE,
    ):
        raise EpochWriteError(f"mark_wb_sync_status: invalid status {status}")
    phase_value = CardAbHoldPhase.WB_SYNC.value
    stmt = _select_adv_for_update(adv_setting_id)
    _ = (await session.execute(stmt)).scalar_one()
    stmt_up = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_id)
        .values(
            card_ab_hold_sync_status=normalized.value,
            card_ab_hold_phase=phase_value,
        )
    )
    _ = await session.execute(stmt_up)
    await session.commit()


async def mark_wb_sync_status(
    adv_setting_id: int,
    status: CardAbHoldSyncStatus | str,
) -> None:
    """Обновить ``card_ab_hold_sync_status`` (partial/complete/pending)."""
    async with sm(read_only=False) as session:
        await mark_wb_sync_status_in_session(session, adv_setting_id, status)


def can_activate_after_successful_sync(adv_setting: Any) -> bool:
    """Pure precondition: intent present + sync complete (§22 ACTIVE gate)."""
    intent = getattr(adv_setting, "card_ab_hold_pending_intent_json", None)
    sync_status = normalize_card_ab_hold_sync_status(
        getattr(adv_setting, "card_ab_hold_sync_status", None)
    )
    return intent is not None and sync_status == CardAbHoldSyncStatus.COMPLETE


async def activate_after_successful_sync_in_session(
    session: AsyncSession,
    adv_setting_id: int,
) -> bool:
    """ACTIVE + READY_ACTIVE при intent + sync complete в переданной session.

    Returns:
        True, если переход выполнен; False, если preconditions не выполнены.
    """
    stmt = _select_adv_for_update(adv_setting_id)
    adv = (await session.execute(stmt)).scalar_one()
    if not can_activate_after_successful_sync(adv):
        logger.info(
            "[adv_setting_id=%s] activate_after_successful_sync skipped: "
            "intent=%s sync_status=%s",
            adv_setting_id,
            getattr(adv, "card_ab_hold_pending_intent_json", None) is not None,
            getattr(adv, "card_ab_hold_sync_status", None),
        )
        return False
    stmt_up = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_id)
        .values(
            card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
            card_ab_hold_phase=CardAbHoldPhase.READY_ACTIVE.value,
        )
    )
    _ = await session.execute(stmt_up)
    await session.commit()
    return True


async def activate_after_successful_sync(adv_setting_id: int) -> bool:
    """ACTIVE + ``READY_ACTIVE`` только при intent + sync complete (§22).

    Returns:
        True, если переход выполнен; False, если preconditions не выполнены.
    """
    async with sm(read_only=False) as session:
        activated = await activate_after_successful_sync_in_session(
            session, adv_setting_id
        )
    if activated:
        logger.info(
            "[adv_setting_id=%s] activate_after_successful_sync → ACTIVE/READY_ACTIVE",
            adv_setting_id,
        )
    return activated


async def clear_epoch_on_exit_in_session(
    session: AsyncSession,
    adv_setting_id: int,
    *,
    commit: bool = True,
) -> None:
    """Сброс epoch-полей в переданной session (§22.5); mode — caller.

    Args:
        session: injectable async write session.
        adv_setting_id: ``AdvSetting.id``.
        commit: выполнить ли commit немедленно. ``False`` позволяет caller
            объединить сброс с другими durable-полями в одной транзакции.
    """
    clears = clear_epoch_fields_values()
    stmt = _select_adv_for_update(adv_setting_id)
    _ = (await session.execute(stmt)).scalar_one()
    stmt_up = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_id)
        .values(**clears)
    )
    _ = await session.execute(stmt_up)
    if commit:
        await session.commit()


async def clear_epoch_on_exit(adv_setting_id: int) -> None:
    """Сброс epoch-полей на EXIT (§22.5); mode обрабатывает caller."""
    async with sm(read_only=False) as session:
        await clear_epoch_on_exit_in_session(session, adv_setting_id)
    logger.info("[adv_setting_id=%s] clear_epoch_on_exit", adv_setting_id)
