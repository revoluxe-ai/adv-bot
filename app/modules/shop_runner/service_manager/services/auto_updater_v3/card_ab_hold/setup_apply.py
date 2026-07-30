"""Persist ENTER-мутаций A/B Hold (legacy MVP-1: OFF + optional ЦП).

Spec ``card-ab-hold-mode`` / tasks §18.4:
- Legacy (``epoch_managed=False``): FAIL → OFF; PASS → target_place = WB position;
  mode → ACTIVE (historical MVP-1).
- Epoch-managed (``epoch_managed=True``): FAIL → OFF Allowed; PASS MUST NOT write
  target_place; MUST NOT set mode ACTIVE (TP only after confirm; ACTIVE only after
  PENDING intent → WB sync).
- Owner A_PRIME / PBH-002: PASS after prior PFO latch → ``recovery_on`` /
  ``return_on`` (strategy_mode restore to MIN_CPA); membership unchanged.

Использует тот же SQLAlchemy update-паттерн, что ``WhiteListTrimmer`` —
без full NORMAL preamble (decision write-path ownership).
"""

from __future__ import annotations

import logging
import math

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    hard_status_for_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.keyword_tp_bulk import (
    bulk_update_keyword_target_places,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_decision import (
    AbHoldSetupAction,
    classify_ab_hold_setup_keyword,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.not_full_target_place import (
    clamp_not_full_target_place,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

# Owner A_PRIME: operable ladder floor when auto_on / restore_on after PFO latch.
_AB_HOLD_RECOVERY_ON_MODE = KeywordStrategyMode.MIN_CPA


def _keyword_strategy_is_off(keyword: CalculatedKeyword) -> bool:
    """True, если текущий ``strategy_mode`` — OFF (PFO safety latch)."""
    mode = getattr(keyword, "strategy_mode", None)
    if mode is None:
        return False
    try:
        return int(mode) == int(KeywordStrategyMode.OFF)
    except (TypeError, ValueError):
        return mode is KeywordStrategyMode.OFF


def ab_hold_target_place_from_keyword(keyword: CalculatedKeyword) -> int | None:
    """Предложенная ЦП из фактической позиции ключа (чистое предложение).

    Spec: после WARM_UP factual vs proposed TP — два поля; confirmed TP только
    после явного confirm. Функция не пишет в PG.
    """
    pos = float(keyword.position)
    if pos <= 0:
        return None
    return clamp_not_full_target_place(int(math.floor(pos + 0.5)))


async def apply_ab_hold_setup_mutations_in_session(
    session: AsyncSession,
    *,
    adv_setting_id: int,
    fail_ids: list[int],
    pass_updates: list[tuple[int, int]],
    snapshot: list[str],
    degraded: bool,
    epoch_managed: bool,
    recovery_on_ids: list[int] | None = None,
) -> None:
    """Persist ENTER FAIL/OFF (+ return_on / legacy ACTIVE/TP) в PG session.

    Args:
        session: injectable async session (WRITE).
        adv_setting_id: ``AdvSetting.id``.
        fail_ids: keyword_setting ids для OFF.
        pass_updates: ``(keyword_setting_id, target_place)`` для legacy PASS.
        snapshot: allowed-phrases snapshot (legacy ACTIVE path).
        degraded: honest degradation flag (legacy ACTIVE path).
        epoch_managed: True — не писать TP/ACTIVE.
        recovery_on_ids: PASS ids previously latched OFF → restore_on (A_PRIME).
    """
    off_hs = hard_status_for_strategy_mode(KeywordStrategyMode.OFF)
    if fail_ids:
        stmt_off = (
            update(KeywordSetting)
            .where(KeywordSetting.id.in_(fail_ids))
            .values(
                hard_status=off_hs,
                strategy_mode=KeywordStrategyMode.OFF,
                target_place=None,
            )
        )
        _ = await session.execute(stmt_off)
    on_ids = list(recovery_on_ids or [])
    if on_ids:
        # pfo_recovery / return_on: strategy only — no TP (epoch) / membership.
        on_hs = hard_status_for_strategy_mode(_AB_HOLD_RECOVERY_ON_MODE)
        stmt_return_on = (
            update(KeywordSetting)
            .where(KeywordSetting.id.in_(on_ids))
            .values(
                hard_status=on_hs,
                strategy_mode=_AB_HOLD_RECOVERY_ON_MODE,
            )
        )
        _ = await session.execute(stmt_return_on)
    if not epoch_managed:
        await bulk_update_keyword_target_places(session, list(pass_updates))
        stmt_mode = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_id)
            .values(
                card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
                card_ab_hold_allowed_phrases_snapshot=snapshot,
                card_ab_hold_degraded=degraded,
            )
        )
        _ = await session.execute(stmt_mode)
    await session.commit()


async def apply_ab_hold_setup_mutations(
    *,
    adv_id: int,
    adv_setting_id: int,
    keywords: list[CalculatedKeyword],
    max_pay_for_order: float,
    allowed_phrases_snapshot: list[str] | None = None,
    degraded: bool = False,
    epoch_managed: bool = False,
) -> tuple[int, int]:
    """Применить ENTER-классификацию; ACTIVE/TP — только для legacy MVP-1.

    Args:
        allowed_phrases_snapshot: PG snapshot разрешённого (allowed/relevant) набора
            фраз (decision §8, primary invariant). MUST быть зафиксирован до ACTIVE
            на legacy-пути; минус — производный enforcement, не хранится здесь.
            Если задан — ``recovery_on`` / auto_on только внутри snapshot
            (Owner A_PRIME: within confirmed set).
        degraded: честная деградация hold (decision §8) — enforcement allowed-set
            превысил WB minus cap на ENTER. Персистится вместе с mode → ACTIVE
            на legacy-пути.
        epoch_managed: True (§18.4) — не писать ``target_place`` на PASS и не
            переводить mode → ACTIVE (epoch path owns confirms / intent / sync).

    Returns:
        (pass_count, fail_count)
    """
    fail_ids: list[int] = []
    recovery_on_ids: list[int] = []
    pass_updates: list[tuple[int, int]] = []
    pass_count = 0
    snapshot_filter: set[str] | None = (
        set(allowed_phrases_snapshot) if allowed_phrases_snapshot is not None else None
    )
    for kw in keywords:
        action = classify_ab_hold_setup_keyword(
            pay_for_order=kw.pay_for_order,
            views=int(kw.views),
            max_pay_for_order=max_pay_for_order,
        )
        ks_id = int(kw.keyword_setting_original_id)
        if action == AbHoldSetupAction.FAIL_OFF:
            fail_ids.append(ks_id)
            continue
        pass_count += 1
        # A_PRIME pfo_recovery: PASS + prior OFF latch → return_on (not membership).
        if _keyword_strategy_is_off(kw):
            text = str(getattr(kw, "text", None) or "")
            if snapshot_filter is None or text in snapshot_filter:
                recovery_on_ids.append(ks_id)
        if epoch_managed:
            # §18.4.2: TP only after explicit tp_confirm — never on ENTER PASS.
            continue
        place = ab_hold_target_place_from_keyword(kw)
        if place is not None:
            pass_updates.append((ks_id, place))

    snapshot: list[str] = (
        list(allowed_phrases_snapshot) if allowed_phrases_snapshot is not None else []
    )
    async with sm(read_only=False) as session:
        await apply_ab_hold_setup_mutations_in_session(
            session,
            adv_setting_id=adv_setting_id,
            fail_ids=fail_ids,
            pass_updates=pass_updates,
            snapshot=snapshot,
            degraded=degraded,
            epoch_managed=epoch_managed,
            recovery_on_ids=recovery_on_ids,
        )

    logger.info(
        "[adv_id=%s] ab_setup applied pass=%s fail=%s recovery_on=%s "
        "allowed_phrases=%s degraded=%s epoch_managed=%s → %s",
        adv_id,
        pass_count,
        len(fail_ids),
        len(recovery_on_ids),
        len(snapshot),
        degraded,
        epoch_managed,
        "PENDING (epoch gate)" if epoch_managed else "ACTIVE",
    )
    return pass_count, len(fail_ids)


async def persist_ab_hold_degraded_flag_in_session(
    session: AsyncSession,
    *,
    adv_setting_id: int,
    degraded: bool,
) -> None:
    """Персистить ``card_ab_hold_degraded`` в переданной PG session."""
    stmt = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_id)
        .values(card_ab_hold_degraded=degraded)
    )
    _ = await session.execute(stmt)
    await session.commit()


async def persist_ab_hold_degraded_flag(
    *,
    adv_setting_id: int,
    degraded: bool,
) -> None:
    """Персистить honest degradation flag A/B Hold в PG (decision §8, durable SoT).

    HOLD-тик (``process_ab_hold``) считает деградацию каждый тик, но mode остаётся
    ACTIVE и отдельного PG-write у тика нет. Флаг durable в PG, т.к. UI-рендер
    (bot-под) читает его независимо от shop-runner-пода, где считается enforcement.
    Self-healing: при чистом enforcement (cap не превышен) флаг снимается.

    Args:
        adv_setting_id: PG id кампании (``AdvSetting.id``).
        degraded: True — enforcement не гарантирует чистый hold (WB minus cap /
            open-match); False — поверхность равна замороженному allowed-set.
    """
    async with sm(read_only=False) as session:
        await persist_ab_hold_degraded_flag_in_session(
            session, adv_setting_id=adv_setting_id, degraded=degraded
        )
    logger.info(
        "[adv_setting_id=%s] ab_hold degraded flag persisted degraded=%s",
        adv_setting_id,
        degraded,
    )
