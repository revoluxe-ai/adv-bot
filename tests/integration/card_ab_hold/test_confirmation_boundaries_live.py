"""Runtime-entrypoint and live-PG evidence for A/B Hold confirmation boundaries.

Тесты проходят через реальные Telegram handlers, ownership relation helper и
epoch write-path на disposable PostgreSQL. Внешний Telegram/Redis transport
остаётся тонким recording-endpoint, а campaign state проверяется повторным
чтением из PG и FSM.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    CardAbHoldSyncStatus,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold import (
    epoch_pipelines,
    keyword_tp_bulk,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3 import (
    target_place_sync,
)
from app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.update_commot_bid_in_search_advs_manager import (
    UpdateCommotBidInSearchAdvsManager,
)
from app.modules.auto_budget_manager.service import AutoBudgetService
from app.client_bot.user_interface.services.adv_excel_roundtrip.import_apply import (
    apply_adv_excel_rows,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write import (
    EpochWriteError,
    confirm_target_places,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    confirm_handlers,
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_callbacks import (
    CahAutoParticipationConfirm,
    CahConfirmDisable,
    CahTpConfirmAll,
    ConfirmStep,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_draft import (
    load_draft,
)
from tests.integration.card_ab_hold._live_pg_bootstrap import (
    disposable_ab_hold_schema,
    ensure_post_epoch_schema_for_orm,
    fetch_adv_epoch_row,
    fetch_keyword_row,
    insert_adv_row,
    insert_keyword_row,
    insert_user_cabinet_relation,
    patched_async_session_maker,
)
from tests.support.destructive_pg_dsn import require_validated_live_pg_dsn_or_skip
from tests.unit.auto_updater_v3.card_ab_hold.confirmation_contract import (
    CAH_EPOCH_FACT_DRIFT_001,
    CAH_EPOCH_PARTIAL_SYNC_001,
    CAH_EPOCH_RETRY_001,
    CAH_LIFECYCLE_CONTRACT,
    CAH_LIFECYCLE_POSITIVE_001,
    CAH_LIFECYCLE_RETRY_001,
    CAH_OWN_ASSOCIATED_001,
    CAH_OWN_FOREIGN_CONFIRM_001,
    CAH_OWN_FOREIGN_DISABLE_001,
    CAH_OWN_UNRELATED_WRITERS_001,
    CAH_TP_EMPTY_001,
    CAH_TP_MIXED_001,
    CAH_TP_POSITIVE_001,
    production_factual_rows,
)


@pytest.fixture(scope="module")
def live_db_url() -> Iterator[str]:
    """Создать отдельную disposable schema для callback-boundary сценариев."""
    db_url = require_validated_live_pg_dsn_or_skip()
    with disposable_ab_hold_schema(db_url):
        ensure_post_epoch_schema_for_orm(db_url)
        yield db_url


def _make_query(*, telegram_id: int) -> MagicMock:
    """Собрать production-shaped CallbackQuery double с Message transport."""
    message = MagicMock(spec=Message)
    message.answer = AsyncMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.message = message
    query.from_user = SimpleNamespace(id=telegram_id)
    query.bot = MagicMock()
    return query


def _make_state(*, telegram_id: int) -> FSMContext:
    """Создать изолированный FSM-контекст конкретного Telegram actor."""
    return FSMContext(
        storage=MemoryStorage(),
        key=StorageKey(bot_id=1, chat_id=1, user_id=telegram_id),
    )


class _RecordingRedisEndpoint:
    """Тонкий Redis endpoint, сохраняющий semantic event вместо call count."""

    def __init__(self, label: str, events: list[str]) -> None:
        self._label = label
        self._events = events

    async def clear(self) -> None:
        """Записать semantic cleanup event для parity assertion."""
        self._events.append(self._label)


@pytest.mark.integration
@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_associated_tp_callback_persists_positive_subset(
    live_db_url: str,
) -> None:
    """S01/S08: связанный actor проходит callback и пишет subset через FOR UPDATE.

    Regression для spec ``card-ab-hold-mode``: valid associated confirmation
    reaches the real epoch writer, persists only positive factual keywords and
    advances the existing confirmation phase.
    """
    owner_case = CAH_OWN_ASSOCIATED_001
    factual_case = CAH_TP_MIXED_001
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=301,
        adv_id=9301,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value,
        extra={
            "card_ab_hold_confirmed_keywords_json": list(factual_case.positions),
            "card_ab_hold_confirmed_target_places_json": None,
        },
    )
    insert_user_cabinet_relation(
        live_db_url,
        user_id=301,
        telegram_id=1301,
        relation_id=3301,
    )
    before_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert before_row[6] is None
    query = _make_query(telegram_id=1301)
    state = _make_state(telegram_id=1301)
    callback_data = CahTpConfirmAll(
        adv_setting_original_id=adv_setting_id,
        step=ConfirmStep.W3_PROPOSE.value,
        revision=1,
        page=0,
    )

    keyword_loader = AsyncMock(return_value=production_factual_rows(factual_case))
    async with patched_async_session_maker(live_db_url):
        with patch(
            "app.client_bot.utils.get_keywords_for_keyboard",
            new=keyword_loader,
        ):
            await confirm_handlers.on_tp_confirm_all(query, callback_data, state)

    assert keyword_loader.await_count >= 1
    assert all(
        call.args[0].id == adv_setting_id
        for call in keyword_loader.await_args_list
    )
    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert row[6] != before_row[6]
    assert row[1] == CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM.value
    assert list(row[5]) == ["alpha"]
    assert dict(row[6]) == {"alpha": 14}
    assert owner_case.expected_neutral_notice is False
    assert "Целевые позиции зафиксированы" in query.message.answer.await_args.args[0]


@pytest.mark.integration
@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_foreign_confirmation_preserves_pg_and_fsm_state(
    live_db_url: str,
) -> None:
    """S02: foreign confirmation stops before stale, FSM mutation, or writer.

    Regression для spec ``card-ab-hold-mode``: PG state and the foreign actor's
    FSM draft are snapshotted before/after the real callback entrypoint; the
    only observable response is a neutral user notification.
    """
    owner_case = CAH_OWN_FOREIGN_CONFIRM_001
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=302,
        adv_id=9302,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value,
        extra={
            "card_ab_hold_confirmed_keywords_json": ["alpha"],
            "card_ab_hold_confirmed_target_places_json": {"alpha": 5},
            "card_ab_hold_generation": 4,
        },
    )
    before_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    query = _make_query(telegram_id=1302)
    state = _make_state(telegram_id=1302)
    before_draft = await load_draft(state, adv_setting_id)
    callback_data = CahTpConfirmAll(
        adv_setting_original_id=adv_setting_id,
        step=ConfirmStep.W3_PROPOSE.value,
        revision=1,
        page=0,
    )

    async with patched_async_session_maker(live_db_url):
        await confirm_handlers.on_tp_confirm_all(query, callback_data, state)

    after_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    after_draft = await load_draft(state, adv_setting_id)
    assert tuple(after_row) == tuple(before_row)
    assert after_draft == before_draft
    notice = query.message.answer.await_args.args[0]
    assert notice == "Доступно только при включённом боте"
    assert owner_case.expected_neutral_notice is True
    assert "9302" not in notice


@pytest.mark.integration
@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_foreign_direct_disable_preserves_pg_and_skips_redis_cleanup(
    live_db_url: str,
) -> None:
    """S03: direct EXIT foreign actor leaves PG and coordination untouched."""
    owner_case = CAH_OWN_FOREIGN_DISABLE_001
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=303,
        adv_id=9303,
        mode=CardAbHoldMode.ACTIVE.value,
        phase=CardAbHoldPhase.READY_ACTIVE.value,
        extra={
            "card_ab_hold_confirmed_keywords_json": ["alpha"],
            "card_ab_hold_confirmed_target_places_json": {"alpha": 7},
            "card_ab_hold_generation": 2,
            "card_ab_hold_pending_intent_json": {"generation": 2},
            "card_ab_hold_allowed_phrases_snapshot": ["alpha"],
        },
    )
    before_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    query = _make_query(telegram_id=1303)
    redis_events: list[str] = []
    signal_cache = lambda _adv: _RecordingRedisEndpoint("signal", redis_events)
    reset_cache = lambda _adv: _RecordingRedisEndpoint("enter-reset", redis_events)
    setup_cache = lambda _adv: _RecordingRedisEndpoint("setup-block", redis_events)

    async with patched_async_session_maker(live_db_url):
        with (
            patch.object(
                handlers,
                "CardAbHoldSignalRedisCache",
                signal_cache,
            ),
            patch.object(
                handlers,
                "CardAbHoldCommonBidEnterResetRedisCache",
                reset_cache,
            ),
            patch.object(
                handlers,
                "CardAbHoldSetupBlockRedisCache",
                setup_cache,
            ),
        ):
            await handlers.disable_card_ab_hold(
                query,
                handlers.CardAbHoldDisable(adv_setting_original_id=adv_setting_id),
            )

    after_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert tuple(after_row) == tuple(before_row)
    assert redis_events == []
    assert owner_case.expected_neutral_notice is True
    assert query.message.answer.await_args.args[0] == "Доступно только при включённом боте"


@pytest.mark.integration
@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_associated_direct_disable_preserves_authorized_exit_cleanup(
    live_db_url: str,
) -> None:
    """S03/2.5: associated EXIT retains the existing PG reset and cleanup."""
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=306,
        adv_id=9306,
        mode=CardAbHoldMode.ACTIVE.value,
        phase=CardAbHoldPhase.READY_ACTIVE.value,
        extra={
            "card_ab_hold_confirmed_keywords_json": ["alpha"],
            "card_ab_hold_confirmed_target_places_json": {"alpha": 9},
            "card_ab_hold_generation": 6,
            "card_ab_hold_pending_intent_json": {"generation": 6},
            "card_ab_hold_allowed_phrases_snapshot": ["alpha"],
        },
    )
    insert_user_cabinet_relation(
        live_db_url,
        user_id=306,
        telegram_id=1306,
        relation_id=3306,
    )
    query = _make_query(telegram_id=1306)
    redis_events: list[str] = []
    signal_cache = lambda _adv: _RecordingRedisEndpoint("signal", redis_events)
    reset_cache = lambda _adv: _RecordingRedisEndpoint("enter-reset", redis_events)
    setup_cache = lambda _adv: _RecordingRedisEndpoint("setup-block", redis_events)

    async with patched_async_session_maker(live_db_url):
        with (
            patch.object(handlers, "CardAbHoldSignalRedisCache", signal_cache),
            patch.object(
                handlers,
                "CardAbHoldCommonBidEnterResetRedisCache",
                reset_cache,
            ),
            patch.object(handlers, "CardAbHoldSetupBlockRedisCache", setup_cache),
        ):
            await handlers.disable_card_ab_hold(
                query,
                handlers.CardAbHoldDisable(adv_setting_original_id=adv_setting_id),
            )

    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert row[0] == CardAbHoldMode.OFF.value
    assert row[1] is None
    assert int(row[4]) == 0
    assert row[5] is None
    assert row[6] is None
    assert row[9] is None
    assert redis_events == ["signal", "enter-reset", "setup-block"]


@pytest.mark.integration
@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_owned_exit_does_not_reach_unrelated_writer_boundaries(
    live_db_url: str,
) -> None:
    """S13: real EXIT owns only the A/B Hold durable effect.

    ``CAH-OWN-UNRELATED-WRITERS-001`` is exercised through the real callback
    and PG writer. Ordinary target-place, shared bid, Excel, budget, and WB
    writer boundaries are probes only; their untouched state is paired with
    the durable before/after snapshot.
    """
    case = CAH_OWN_UNRELATED_WRITERS_001
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=310,
        adv_id=9310,
        mode=CardAbHoldMode.ACTIVE.value,
        phase=CardAbHoldPhase.READY_ACTIVE.value,
        extra={
            "card_ab_hold_confirmed_keywords_json": ["alpha"],
            "card_ab_hold_confirmed_target_places_json": {"alpha": 9},
            "card_ab_hold_generation": 8,
            "card_ab_hold_pending_intent_json": {"generation": 8},
            "card_ab_hold_allowed_phrases_snapshot": ["alpha"],
        },
    )
    insert_user_cabinet_relation(
        live_db_url,
        user_id=310,
        telegram_id=1310,
        relation_id=3310,
    )
    before_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    query = _make_query(telegram_id=1310)
    redis_events: list[str] = []
    probes = {
        "ordinary": AsyncMock(),
        "shared": AsyncMock(),
        "excel": AsyncMock(),
        "bid": AsyncMock(),
        "budget": AsyncMock(),
        "wb": AsyncMock(),
    }

    async with patched_async_session_maker(live_db_url):
        with (
            patch.object(
                handlers,
                "CardAbHoldSignalRedisCache",
                lambda _adv: _RecordingRedisEndpoint("signal", redis_events),
            ),
            patch.object(
                handlers,
                "CardAbHoldCommonBidEnterResetRedisCache",
                lambda _adv: _RecordingRedisEndpoint("enter-reset", redis_events),
            ),
            patch.object(
                handlers,
                "CardAbHoldSetupBlockRedisCache",
                lambda _adv: _RecordingRedisEndpoint("setup-block", redis_events),
            ),
            patch.object(
                target_place_sync,
                "sync_keyword_target_places_v3",
                new=probes["ordinary"],
            ),
            patch.object(
                keyword_tp_bulk,
                "bulk_update_keyword_target_places",
                new=probes["shared"],
            ),
            patch.object(
                UpdateCommotBidInSearchAdvsManager,
                "update_common_bid_in_search_adv",
                new=probes["bid"],
            ),
            patch.object(
                AutoBudgetService,
                "ensure_budget",
                new=probes["budget"],
            ),
            patch(
                "app.client_bot.user_interface.services.adv_excel_roundtrip.import_apply.apply_adv_excel_rows",
                new=probes["excel"],
            ),
            patch.object(
                epoch_pipelines,
                "sync_intent_to_wb",
                new=probes["wb"],
            ),
        ):
            await handlers.disable_card_ab_hold(
                query,
                handlers.CardAbHoldDisable(adv_setting_original_id=adv_setting_id),
            )

    after_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert tuple(after_row) != tuple(before_row)
    assert after_row[0] == CardAbHoldMode.OFF.value
    assert after_row[1] is None
    assert int(after_row[4]) == 0
    assert after_row[5] is None
    assert after_row[6] is None
    assert after_row[9] is None
    assert redis_events == ["signal", "enter-reset", "setup-block"]
    assert case.expected_neutral_notice is False
    for probe in probes.values():
        probe.assert_not_awaited()


@pytest.mark.integration
@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_foreign_confirm_flow_disable_preserves_pg_and_fsm_state(
    live_db_url: str,
) -> None:
    """S03: confirm-flow EXIT foreign actor cannot reset durable or FSM state."""
    owner_case = CAH_OWN_FOREIGN_DISABLE_001
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=304,
        adv_id=9304,
        mode=CardAbHoldMode.ACTIVE.value,
        phase=CardAbHoldPhase.READY_ACTIVE.value,
        extra={
            "card_ab_hold_confirmed_keywords_json": ["alpha"],
            "card_ab_hold_confirmed_target_places_json": {"alpha": 8},
            "card_ab_hold_generation": 3,
            "card_ab_hold_pending_intent_json": {"generation": 3},
        },
    )
    before_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    query = _make_query(telegram_id=1304)
    state = _make_state(telegram_id=1304)
    before_draft = await load_draft(state, adv_setting_id)
    callback_data = CahConfirmDisable(
        adv_setting_original_id=adv_setting_id,
        step=ConfirmStep.S3.value,
        revision=1,
    )

    async with patched_async_session_maker(live_db_url):
        await confirm_handlers.on_confirm_disable(query, callback_data, state)

    after_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    after_draft = await load_draft(state, adv_setting_id)
    assert tuple(after_row) == tuple(before_row)
    assert after_draft == before_draft
    notice = query.message.answer.await_args.args[0]
    assert notice == "Доступно только при включённом боте"
    assert owner_case.expected_neutral_notice is True
    assert "9304" not in notice


@pytest.mark.integration
@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_empty_valid_target_set_stops_live_callback(
    live_db_url: str,
) -> None:
    """S09: пустой valid-set останавливает callback до durable writer."""
    factual_case = CAH_TP_EMPTY_001
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=307,
        adv_id=9307,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value,
        extra={
            "card_ab_hold_confirmed_keywords_json": list(factual_case.positions),
            "card_ab_hold_confirmed_target_places_json": None,
        },
    )
    insert_user_cabinet_relation(
        live_db_url,
        user_id=307,
        telegram_id=1307,
        relation_id=3307,
    )
    before_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    query = _make_query(telegram_id=1307)
    state = _make_state(telegram_id=1307)
    callback_data = CahTpConfirmAll(
        adv_setting_original_id=adv_setting_id,
        step=ConfirmStep.W3_PROPOSE.value,
        revision=1,
        page=0,
    )

    keyword_loader = AsyncMock(return_value=production_factual_rows(factual_case))
    async with patched_async_session_maker(live_db_url):
        with patch(
            "app.client_bot.utils.get_keywords_for_keyboard",
            new=keyword_loader,
        ):
            await confirm_handlers.on_tp_confirm_all(query, callback_data, state)

    assert keyword_loader.await_count >= 1
    after_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert tuple(after_row) == tuple(before_row)
    notice = query.message.answer.await_args.args[0]
    assert (
        notice
        == "Нет валидных ключей для подтверждения: фактические позиции "
        "отсутствуют или неположительны."
    )
    assert "0" not in notice


@pytest.mark.integration
@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_epoch_retry_reuses_confirmed_target_and_generation(
    live_db_url: str,
) -> None:
    """S10: partial WB sync retry reuses durable target and generation.

    Regression для spec ``card-ab-hold-mode``: the real epoch orchestration
    performs PG apply/row-lock and retry transitions while only the external WB
    transport is made to fail once; no target proposal or generation bump occurs.
    """
    retry_case = CAH_EPOCH_RETRY_001
    partial_case = CAH_EPOCH_PARTIAL_SYNC_001
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=305,
        adv_id=9305,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.PENDING_INTENT.value,
        extra={
            "card_ab_hold_confirmed_keywords_json": list(retry_case.keywords),
            "card_ab_hold_confirmed_target_places_json": {"alpha": 7},
            "card_ab_hold_pending_intent_json": {
                "generation": 5,
                "keywords": list(retry_case.keywords),
                "target_places": {"alpha": 7},
                "auto_participation": False,
                "auto_bid": 0,
            },
            "card_ab_hold_generation": 5,
            "card_ab_hold_sync_status": CardAbHoldSyncStatus.PENDING.value,
        },
    )
    keyword_id = insert_keyword_row(
        live_db_url,
        keyword_id=3305,
        adv_setting_id=adv_setting_id,
        text_value="alpha",
        target_place=7,
    )
    adv_setting = SimpleNamespace(
        id=adv_setting_id,
        card_ab_hold_phase=CardAbHoldPhase.PENDING_INTENT.value,
        card_ab_hold_sync_status=CardAbHoldSyncStatus.PENDING.value,
        card_ab_hold_pending_intent_json={
            "generation": 5,
            "keywords": ["alpha"],
            "target_places": {"alpha": 7},
            "auto_participation": False,
            "auto_bid": 0,
        },
        card_ab_hold_generation=5,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_degraded=False,
    )
    complex_adv = SimpleNamespace(
        adv_id=9305,
        shop_id=1,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        adv_setting=adv_setting,
        nmids=[],
        auto_adv_id=None,
    )
    wb_sync = AsyncMock(side_effect=[RuntimeError(partial_case.failure_message), None])

    async with patched_async_session_maker(live_db_url):
        with (
            patch.object(
                epoch_pipelines,
                "ensure_search_common_bid_reset_on_enter",
                new=AsyncMock(),
            ),
            patch.object(epoch_pipelines, "sync_intent_to_wb", new=wb_sync),
        ):
            await epoch_pipelines.process_ab_epoch(
                complex_adv,
                wb_shop_data_manager=MagicMock(),
                wb_manager_hub=MagicMock(),
            )
            first_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
            first_keyword = fetch_keyword_row(live_db_url, keyword_id)
            await epoch_pipelines.process_ab_epoch(
                complex_adv,
                wb_shop_data_manager=MagicMock(),
                wb_manager_hub=MagicMock(),
            )

    second_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    second_keyword = fetch_keyword_row(live_db_url, keyword_id)
    assert first_row[4] == 5
    assert second_row[4] == 5
    assert dict(first_row[6]) == {"alpha": 7}
    assert dict(second_row[6]) == {"alpha": 7}
    assert first_keyword[2] == 7
    assert second_keyword[2] == 7
    assert second_row[10] == CardAbHoldSyncStatus.COMPLETE.value
    assert second_row[1] == CardAbHoldPhase.READY_ACTIVE.value
    assert wb_sync.await_count == 2
    assert retry_case.case_id == "CAH-EPOCH-RETRY-001"
    assert partial_case.case_id == "CAH-EPOCH-PARTIAL-SYNC-001"


@pytest.mark.integration
@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_fact_drift_rereads_pg_target_without_reopening_confirmation(
    live_db_url: str,
) -> None:
    """S11: live PG target survives factual drift and remains read-only."""
    case = CAH_EPOCH_FACT_DRIFT_001
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=309,
        adv_id=9309,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM.value,
        extra={
            "card_ab_hold_confirmed_keywords_json": ["alpha"],
            "card_ab_hold_confirmed_target_places_json": {
                "alpha": case.confirmed_target_place
            },
            "card_ab_hold_generation": 7,
        },
    )
    before_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    query = _make_query(telegram_id=1309)
    state = _make_state(telegram_id=1309)
    factual_rows = production_factual_rows(CAH_TP_POSITIVE_001)
    factual_rows[0].cluster_stat.position = case.factual_position
    factual_loader = AsyncMock(return_value=factual_rows)

    async with patched_async_session_maker(live_db_url):
        with patch(
            "app.client_bot.utils.get_keywords_for_keyboard",
            new=factual_loader,
        ):
            adv = await confirm_handlers._load_adv(adv_setting_id)
            assert adv is not None
            await confirm_handlers._render_for_adv(query, adv, state)

    assert factual_loader.await_count >= 1
    assert all(
        call.args[0].id == adv_setting_id
        for call in factual_loader.await_args_list
    )
    after_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert tuple(after_row) == tuple(before_row)
    text = query.message.edit_text.await_args.args[0]
    assert "факт: 18" in text
    assert "цель: 7 (зафиксирована)" in text
    assert "Подтвердить целевые позиции" not in text


@pytest.mark.integration
@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_accepts_complete_positive_target_payload(
    live_db_url: str,
) -> None:
    """S09/4.1: полный положительный payload проходит через ``FOR UPDATE``."""
    case = CAH_TP_POSITIVE_001
    keyword, target = next(iter(case.expected_rows))[0], next(iter(case.expected_rows))[2]
    adv_setting_id = 499
    insert_adv_row(
        live_db_url,
        adv_setting_id=adv_setting_id,
        adv_id=9499,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value,
        extra={
            "card_ab_hold_confirmed_keywords_json": [keyword],
            "card_ab_hold_confirmed_target_places_json": None,
        },
    )

    async with patched_async_session_maker(live_db_url):
        await confirm_target_places(adv_setting_id, {keyword: target})

    after_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert after_row[1] == CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM.value
    assert dict(after_row[6]) == {keyword: target}


@pytest.mark.integration
@pytest.mark.destructive_local
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"alpha": 0},
        {"alpha": -1},
        {"alpha": True},
        {"alpha": 1.5},
        {"foreign": 5},
    ],
)
async def test_live_pg_rejects_invalid_target_payload_before_update(
    live_db_url: str,
    payload: dict[str, object],
) -> None:
    """S09/4.1: live ``FOR UPDATE`` writer rejects invalid payload atomically."""
    adv_setting_id = 400 + abs(hash(repr(payload))) % 100
    insert_adv_row(
        live_db_url,
        adv_setting_id=adv_setting_id,
        adv_id=9400 + adv_setting_id,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value,
        extra={
            "card_ab_hold_confirmed_keywords_json": ["alpha", "beta"],
            "card_ab_hold_confirmed_target_places_json": {"alpha": 5},
        },
    )
    before_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)

    async with patched_async_session_maker(live_db_url):
        with pytest.raises(EpochWriteError):
            await confirm_target_places(adv_setting_id, payload)

    after_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert tuple(after_row) == tuple(before_row)


@pytest.mark.integration
@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_full_confirmation_lifecycle_preserves_epoch_and_retry_boundaries(
    live_db_url: str,
) -> None:
    """S12: full confirmation sequence reaches durable intent and ACTIVE.

    ContractCase ``CAH-LIFECYCLE-POSITIVE-001`` / ``CAH-LIFECYCLE-RETRY-001``:
    real Telegram handlers and PG epoch writers perform the complete
    confirmation sequence; the real epoch pipeline performs PG apply and
    activation. Telegram Message, WB transport, and Redis common-bid
    coordination are thin ends, so this test is intentionally authored as
    destructive-local evidence and is not run without authorization.
    """
    assert CAH_LIFECYCLE_CONTRACT.case_id == CAH_LIFECYCLE_POSITIVE_001
    assert CAH_LIFECYCLE_CONTRACT.retry_case_id == CAH_LIFECYCLE_RETRY_001
    adv_setting_id = 308
    adv_id = 9308
    insert_adv_row(
        live_db_url,
        adv_setting_id=adv_setting_id,
        adv_id=adv_id,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value,
        extra={
            "card_ab_hold_confirmed_keywords_json": ["alpha"],
            "card_ab_hold_confirmed_target_places_json": None,
        },
    )
    keyword_id = insert_keyword_row(
        live_db_url,
        keyword_id=3308,
        adv_setting_id=adv_setting_id,
        text_value="alpha",
        target_place=99,
    )
    insert_user_cabinet_relation(
        live_db_url,
        user_id=308,
        telegram_id=1308,
        relation_id=3308,
    )
    query = _make_query(telegram_id=1308)
    state = _make_state(telegram_id=1308)
    tp_callback = CahTpConfirmAll(
        adv_setting_original_id=adv_setting_id,
        step=ConfirmStep.W3_PROPOSE.value,
        revision=1,
        page=0,
    )
    auto_callback = CahAutoParticipationConfirm(
        adv_setting_original_id=adv_setting_id,
        step=ConfirmStep.A1.value,
        revision=2,
        participates=0,
    )
    factual_rows = production_factual_rows(CAH_TP_POSITIVE_001)
    factual_loader = AsyncMock(return_value=factual_rows)

    async with patched_async_session_maker(live_db_url):
        with (
            patch(
                "app.client_bot.utils.get_keywords_for_keyboard",
                new=factual_loader,
            ),
            patch.object(
                epoch_pipelines,
                "ensure_search_common_bid_reset_on_enter",
                new=AsyncMock(),
            ) as redis_reset,
            patch.object(
                epoch_pipelines,
                "sync_intent_to_wb",
                new=AsyncMock(),
            ) as wb_sync,
        ):
            await confirm_handlers.on_tp_confirm_all(query, tp_callback, state)
            await confirm_handlers.on_auto_participation_confirm(
                query,
                auto_callback,
                state,
            )

            pending_row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
            pending_intent = dict(pending_row[9])
            adv_setting = SimpleNamespace(
                id=adv_setting_id,
                card_ab_hold_phase=pending_row[1],
                card_ab_hold_sync_status=pending_row[10],
                card_ab_hold_pending_intent_json=pending_intent,
                card_ab_hold_generation=pending_row[4],
                card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
                card_ab_hold_degraded=False,
            )
            complex_adv = SimpleNamespace(
                adv_id=adv_id,
                card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
                adv_setting=adv_setting,
                nmids=[],
                auto_adv_id=None,
            )
            await epoch_pipelines.process_ab_epoch(
                complex_adv,
                wb_shop_data_manager=MagicMock(),
                wb_manager_hub=MagicMock(),
            )

    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    keyword_row = fetch_keyword_row(live_db_url, keyword_id)
    assert row[0] == CardAbHoldMode.ACTIVE.value
    assert row[1] == CardAbHoldPhase.READY_ACTIVE.value
    assert row[4] == 1
    assert dict(row[6]) == {"alpha": 7}
    assert dict(row[9])["target_places"] == {"alpha": 7}
    assert row[10] == CardAbHoldSyncStatus.COMPLETE.value
    assert keyword_row[2] == 7
    factual_loader.assert_awaited_once()
    assert redis_reset.await_count == len(CAH_LIFECYCLE_CONTRACT.redis_enter_events)
    assert wb_sync.await_count == CAH_LIFECYCLE_CONTRACT.wb_sync_calls
    assert (
        query.message.answer.await_count
        >= CAH_LIFECYCLE_CONTRACT.minimum_telegram_notifications
    )
    query.answer.assert_not_awaited()
