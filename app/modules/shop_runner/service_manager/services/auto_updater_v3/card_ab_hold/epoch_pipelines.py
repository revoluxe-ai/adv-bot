"""Shop-runner epoch tick: WARM_UP elapsed + PENDING intent WB sync (§19–§22).

Owner write-path: ``ab-hold-epoch-lifecycle-and-generation-ownership``,
``card-ab-hold-write-path-ownership``. Legacy ``process_ab_setup`` (phase NULL)
не затрагивается — epoch-managed кампании обрабатываются здесь.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import select, update

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    CardAbHoldSyncStatus,
    is_warmup_elapsed,
    normalize_card_ab_hold_sync_status,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write import (
    activate_after_successful_sync,
    advance_warmup_to_tp_confirm,
    mark_wb_sync_status,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.minus_freeze import (
    normalize_allowed_snapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
    is_epoch_managed_ab_hold,
    normalize_card_ab_hold_mode,
    normalize_card_ab_hold_phase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.stale_stats_freeze import (
    should_freeze_keyword_and_bid_mutations,
)
from app.modules.shop_runner.service_manager.services.minus_phrase_manager import (
    MinusPhraseManagerContainer,
)
from app.utils.db.session_maker import get_async_session_maker as sm

if TYPE_CHECKING:
    from app.core.di.wb_manager_hub import WBManagerHub
    from app.modules.shop_runner.service_manager.wb_shop_data_manager import (
        ComplexAdv,
        WBShopDataManager,
    )

logger = logging.getLogger(__name__)


async def _apply_activation_to_complex_adv(
    complex_adv: "ComplexAdv",
    *,
    generation: int | None = None,
) -> bool:
    """Завершить activation после durable ``sync_status=complete``.

    Не трогает WB / intent apply. Ошибки activation логируются и не демоитят
    ``complete`` в ``partial`` (invariant ab-hold-complete-sync-activate-only).

    Args:
        complex_adv: кампания с epoch-полями на ``adv_setting``.
        generation: опциональный generation для лога.

    Returns:
        True, если PG-переход в ACTIVE выполнен.
    """
    adv_setting_id = int(complex_adv.adv_setting.id)
    try:
        activated = await activate_after_successful_sync(adv_setting_id)
    except Exception as exc:
        logger.error(
            "[adv_id=%s] ab_epoch: activation after complete failed generation=%s: %s",
            complex_adv.adv_id,
            generation,
            exc,
            exc_info=True,
        )
        return False
    if activated:
        complex_adv.adv_setting.card_ab_hold_mode = CardAbHoldMode.ACTIVE.value
        complex_adv.adv_setting.card_ab_hold_phase = (
            CardAbHoldPhase.READY_ACTIVE.value
        )
        cast(Any, complex_adv).card_ab_hold_mode = CardAbHoldMode.ACTIVE.value
        logger.info(
            "[adv_id=%s] ab_epoch: generation=%s complete → ACTIVE (activate-only)",
            complex_adv.adv_id,
            generation,
        )
    return activated


async def process_ab_epoch(
    complex_adv: "ComplexAdv",
    *,
    wb_shop_data_manager: "WBShopDataManager",
    wb_manager_hub: "WBManagerHub",
    stats_fresh: bool = True,
) -> None:
    """Epoch-managed tick для ``PENDING_SETUP`` (§19 WARM_UP / §22 WB sync).

    После durable ``card_ab_hold_sync_status=complete`` tick только завершает
    activation и не повторяет intent/WB sync для той же generation; ``pending`` /
    ``partial`` остаются eligible для WB retry. Phase MAY оставаться ``WB_SYNC``.

    Args:
        complex_adv: кампания с ``adv_setting`` epoch-полями.
        wb_shop_data_manager: контекст shop-runner (reserved для parity с setup/hold).
        wb_manager_hub: WB write-path для sync intent.
        stats_fresh: False при stale/missing stats — keyword/WB мутации §23 skip
            (не блокирует activate-only после complete).
    """
    _ = wb_shop_data_manager
    if not is_epoch_managed_ab_hold(complex_adv.adv_setting):
        return

    mode = normalize_card_ab_hold_mode(complex_adv.card_ab_hold_mode)
    if mode != CardAbHoldMode.PENDING_SETUP:
        return

    adv_setting = complex_adv.adv_setting
    adv_setting_id = int(adv_setting.id)
    phase = normalize_card_ab_hold_phase(getattr(adv_setting, "card_ab_hold_phase", None))

    if phase == CardAbHoldPhase.WARM_UP:
        started_at = getattr(adv_setting, "card_ab_hold_warmup_started_at", None)
        duration = int(getattr(adv_setting, "card_ab_hold_warmup_duration_hours", 24) or 24)
        if is_warmup_elapsed(started_at, duration):
            advanced = await advance_warmup_to_tp_confirm(adv_setting_id)
            if advanced:
                adv_setting.card_ab_hold_phase = (
                    CardAbHoldPhase.AWAITING_TP_CONFIRM.value
                )
        return

    sync_status = normalize_card_ab_hold_sync_status(
        getattr(adv_setting, "card_ab_hold_sync_status", None)
    )
    # Residual complete: activate-only before needs_sync / §23 freeze / WB body.
    if sync_status == CardAbHoldSyncStatus.COMPLETE:
        intent_raw = getattr(adv_setting, "card_ab_hold_pending_intent_json", None)
        generation: int | None = None
        if isinstance(intent_raw, dict):
            generation = int(intent_raw.get("generation", 0) or 0)
        await _apply_activation_to_complex_adv(
            complex_adv,
            generation=generation,
        )
        return

    needs_sync = phase in (
        CardAbHoldPhase.PENDING_INTENT,
        CardAbHoldPhase.WB_SYNC,
    ) or sync_status in (
        CardAbHoldSyncStatus.PENDING,
        CardAbHoldSyncStatus.PARTIAL,
    )
    if not needs_sync:
        return

    intent_raw = getattr(adv_setting, "card_ab_hold_pending_intent_json", None)
    if not intent_raw or not isinstance(intent_raw, dict):
        logger.error(
            "[adv_id=%s] ab_epoch: PENDING/WB_SYNC without durable intent — "
            "stay non-ACTIVE",
            complex_adv.adv_id,
        )
        return

    intent = cast(dict[str, Any], intent_raw)

    if should_freeze_keyword_and_bid_mutations(
        mode=mode,
        phase=getattr(adv_setting, "card_ab_hold_phase", None),
        stats_fresh=stats_fresh,
    ):
        logger.info(
            "[adv_id=%s] ab_epoch: stale stats freeze — skip WB sync (§23)",
            complex_adv.adv_id,
        )
        return

    generation = int(intent.get("generation", 0) or 0)
    try:
        await apply_confirmed_intent_to_pg(
            adv_setting_id=adv_setting_id,
            intent=intent,
        )
        await sync_intent_to_wb(
            complex_adv,
            intent=intent,
            wb_manager_hub=wb_manager_hub,
        )
        await mark_wb_sync_status(adv_setting_id, CardAbHoldSyncStatus.COMPLETE)
        adv_setting.card_ab_hold_sync_status = CardAbHoldSyncStatus.COMPLETE.value
    except Exception as exc:
        logger.error(
            "[adv_id=%s] ab_epoch: WB sync partial/fail generation=%s: %s",
            complex_adv.adv_id,
            generation,
            exc,
            exc_info=True,
        )
        await mark_wb_sync_status(adv_setting_id, CardAbHoldSyncStatus.PARTIAL)
        adv_setting.card_ab_hold_sync_status = CardAbHoldSyncStatus.PARTIAL.value
        adv_setting.card_ab_hold_phase = CardAbHoldPhase.WB_SYNC.value
        return

    # Durable complete: activation errors must not reopen WB via PARTIAL.
    await _apply_activation_to_complex_adv(
        complex_adv,
        generation=generation,
    )


async def apply_confirmed_intent_to_pg(
    *,
    adv_setting_id: int,
    intent: dict[str, Any],
) -> None:
    """Записать confirmed TP и allowed-set snapshot в PG (без пересчёта, §22).

    Использует только ``intent["target_places"]`` и ``intent["keywords"]`` —
    никогда не вызывает классификатор setup или propose TP.
    """
    target_places: dict[str, int] = dict(intent.get("target_places") or {})
    keywords_list: list[str] = list(intent.get("keywords") or [])
    allowed_snapshot = normalize_allowed_snapshot(keywords_list)

    async with sm(read_only=False) as session:
        stmt = select(KeywordSetting).where(
            KeywordSetting.adv_setting_id == adv_setting_id
        )
        result = await session.execute(stmt)
        keyword_rows = result.scalars().all()
        text_to_id: dict[str, int] = {
            str(kw.text).lower(): int(kw.id) for kw in keyword_rows
        }
        for keyword_text, place in target_places.items():
            ks_id = text_to_id.get(str(keyword_text).lower())
            if ks_id is None:
                logger.warning(
                    "[adv_setting_id=%s] apply_confirmed_intent: keyword %r "
                    "not found in PG — skip TP",
                    adv_setting_id,
                    keyword_text,
                )
                continue
            stmt_tp = (
                update(KeywordSetting)
                .where(KeywordSetting.id == ks_id)
                .values(target_place=int(place))
            )
            _ = await session.execute(stmt_tp)

        stmt_adv = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_id)
            .values(
                card_ab_hold_allowed_phrases_snapshot=allowed_snapshot,
                card_ab_hold_phase=CardAbHoldPhase.WB_SYNC.value,
            )
        )
        _ = await session.execute(stmt_adv)
        await session.commit()

    logger.info(
        "[adv_setting_id=%s] apply_confirmed_intent_to_pg: tp=%s allowed=%s",
        adv_setting_id,
        len(target_places),
        len(allowed_snapshot),
    )


async def sync_intent_to_wb(
    complex_adv: "ComplexAdv",
    *,
    intent: dict[str, Any],
    wb_manager_hub: "WBManagerHub",
) -> None:
    """Синхронизировать confirmed intent на WB (allowed-set + Auto CPM, §22).

    Raises:
        Exception: любая ошибка WB → caller помечает sync partial.
    """
    keywords_list: list[str] = list(intent.get("keywords") or [])
    allowed_snapshot = normalize_allowed_snapshot(keywords_list)
    auto_participation = bool(intent.get("auto_participation", False))
    auto_bid = float(intent.get("auto_bid") or 0)

    minus_mgr = MinusPhraseManagerContainer(
        _wb_api_manager_hub=wb_manager_hub
    ).minus_phrase_manager()
    enforce = await minus_mgr.enforce_frozen_allowed_set(
        complex_adv, allowed_snapshot
    )
    if enforce.get("cap_exceeded"):
        logger.warning(
            "[adv_id=%s] sync_intent_to_wb: allowed-set cap exceeded — "
            "continuing with partial enforcement",
            complex_adv.adv_id,
        )

    if auto_participation and auto_bid > 0:
        nmids = list(complex_adv.nmids or [])
        if not nmids:
            raise ValueError("auto_participation confirmed but nmids empty")
        auto_adv_id = int(complex_adv.auto_adv_id)
        nm_bid_pairs = {int(nmid): int(auto_bid) for nmid in nmids}
        await wb_manager_hub.wb_modifier.update_auto_adv_cpm(
            auto_adv_id, nm_bid_pairs
        )
        logger.info(
            "[adv_id=%s] sync_intent_to_wb: auto CPM=%s nmids=%s",
            complex_adv.adv_id,
            auto_bid,
            len(nmids),
        )
