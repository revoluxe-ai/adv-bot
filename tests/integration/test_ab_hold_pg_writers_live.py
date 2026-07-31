"""Live PG re-read coverage for A/B Hold writers (external-call PG gaps).

Requires validated ``TEST_DATABASE_URL`` + ``ALLOW_DESTRUCTIVE_TEST_DB=1``.
Proves durable writes via production ``sm`` seam (patched to disposable DB)
+ SQL re-select — not session AsyncMock. Не marker ``fast``.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    CardAbHoldSyncStatus,
    DEFAULT_WARMUP_HOURS,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_pipelines import (
    apply_confirmed_intent_to_pg,
    apply_confirmed_intent_to_pg_in_session,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write import (
    activate_after_successful_sync,
    advance_warmup_to_tp_confirm,
    clear_epoch_on_exit,
    confirm_auto_bid,
    confirm_auto_participation,
    confirm_keyword_set_and_start_warmup,
    confirm_target_places,
    mark_wb_sync_status,
    set_warmup_duration,
    start_epoch_on_enable,
    start_epoch_on_enable_in_session,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.hold_guards import (
    apply_ab_hold_overspend_offs,
    apply_ab_hold_overspend_offs_in_session,
    apply_ab_hold_pfo_recovery_ons,
    apply_ab_hold_pfo_recovery_ons_in_session,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_apply import (
    apply_ab_hold_setup_mutations,
    persist_ab_hold_degraded_flag,
    persist_ab_hold_degraded_flag_in_session,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldDisable,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_handlers import (
    _abort_epoch_to_off,
    _load_adv,
    _load_adv_in_session,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.handlers import (
    disable_card_ab_hold,
    load_adv_setting_after_enable,
    load_adv_setting_for_ab_hold_menu,
    load_adv_setting_for_back,
    load_adv_setting_for_enable_gates,
)
from tests.integration.card_ab_hold._live_pg_bootstrap import (
    disposable_ab_hold_schema,
    ensure_post_epoch_schema_for_orm,
    fetch_adv_degraded_flag,
    fetch_adv_epoch_row,
    fetch_keyword_row,
    insert_adv_row,
    insert_keyword_row,
    patched_async_session_maker,
)
from tests.support.destructive_pg_dsn import require_validated_live_pg_dsn_or_skip

_HANDLERS = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.telegram.handlers"
)
_CONFIRM = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.telegram.confirm_handlers"
)


@pytest.fixture(scope="module")
def live_db_url() -> Iterator[str]:
    """Disposable schema на модуль; невалидный DSN → fail-closed error."""
    db_url = require_validated_live_pg_dsn_or_skip()
    with disposable_ab_hold_schema(db_url):
        ensure_post_epoch_schema_for_orm(db_url)
        yield db_url


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_start_epoch_on_enable_persists_mode_phase(
    live_db_url: str,
) -> None:
    """``start_epoch_on_enable`` → PENDING_SETUP + AWAITING_KEYWORD_CONFIRM."""
    adv_setting_id = insert_adv_row(
        live_db_url, adv_setting_id=101, adv_id=9101, mode="off", phase=None
    )
    async with patched_async_session_maker(live_db_url):
        with patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_write.can_enter_epoch_managed_ab_hold",
            return_value=True,
        ):
            managed = await start_epoch_on_enable(adv_setting_id, adv_id=9101)

    assert managed is True
    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert row[0] == CardAbHoldMode.PENDING_SETUP.value
    assert row[1] == CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM.value


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_confirm_handlers_load_adv_uses_read_replica_mode(
    live_db_url: str,
) -> None:
    """``_load_adv`` читает AdvSetting через production ``sm(read_only=True)`` seam."""
    adv_setting_id = insert_adv_row(
        live_db_url, adv_setting_id=1001, adv_id=9901, mode="off", phase=None
    )
    async with patched_async_session_maker(live_db_url):
        adv = await _load_adv(adv_setting_id)

    assert adv is not None
    assert int(adv.id) == adv_setting_id


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_warmup_keyword_and_duration_writers(live_db_url: str) -> None:
    """``confirm_keyword_set`` + ``set_warmup_duration`` durable WARM_UP timer."""
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=102,
        adv_id=9102,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM.value,
    )
    async with patched_async_session_maker(live_db_url):
        await confirm_keyword_set_and_start_warmup(
            adv_setting_id, ["alpha", "beta"], duration_hours=24
        )
        applied = await set_warmup_duration(adv_setting_id, 48)

    assert applied == 48
    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert row[1] == CardAbHoldPhase.WARM_UP.value
    assert row[2] is not None  # warmup_started_at
    assert int(row[3]) == 48
    assert list(row[5]) == ["alpha", "beta"]


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_epoch_confirm_sync_activate_and_clear(
    live_db_url: str,
) -> None:
    """Цепочка TP→auto→intent sync→ACTIVE + ``clear_epoch_on_exit`` re-read."""
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=103,
        adv_id=9103,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.WARM_UP.value,
        extra={
            "card_ab_hold_confirmed_keywords_json": ["alpha"],
            "card_ab_hold_warmup_duration_hours": 24,
        },
    )
    async with patched_async_session_maker(live_db_url):
        assert await advance_warmup_to_tp_confirm(adv_setting_id) is True
        await confirm_target_places(adv_setting_id, {"alpha": 5})
        await confirm_auto_participation(adv_setting_id, True)
        created = await confirm_auto_bid(adv_setting_id, 120.0)
        assert created is True
        await mark_wb_sync_status(adv_setting_id, CardAbHoldSyncStatus.COMPLETE)
        # Intent still present — mark_wb_sync only updates sync/phase.
        mid = fetch_adv_epoch_row(live_db_url, adv_setting_id)
        assert mid[9] is not None
        assert mid[10] == CardAbHoldSyncStatus.COMPLETE.value
        assert await activate_after_successful_sync(adv_setting_id) is True
        await clear_epoch_on_exit(adv_setting_id)

    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    # clear_epoch clears phase/intent; mode is caller's job — remains ACTIVE here.
    assert row[0] == CardAbHoldMode.ACTIVE.value
    assert row[1] is None
    assert row[2] is None
    assert int(row[3]) == DEFAULT_WARMUP_HOURS
    assert int(row[4]) == 0
    assert row[5] is None
    assert row[6] is None
    assert row[7] is None
    assert row[8] is None
    assert row[9] is None
    assert row[10] == CardAbHoldSyncStatus.NONE.value
    assert row[11] is None


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_apply_confirmed_intent_writes_tp_and_snapshot(
    live_db_url: str,
) -> None:
    """``apply_confirmed_intent_to_pg`` → KeywordSetting.target_place + snapshot."""
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=104,
        adv_id=9104,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.PENDING_INTENT.value,
    )
    insert_keyword_row(
        live_db_url,
        keyword_id=2004,
        adv_setting_id=adv_setting_id,
        text_value="alpha",
        target_place=None,
    )
    intent = {
        "keywords": ["alpha"],
        "target_places": {"alpha": 9},
        "auto_participation": True,
        "auto_bid": 50.0,
        "generation": 1,
    }
    async with patched_async_session_maker(live_db_url):
        await apply_confirmed_intent_to_pg(
            adv_setting_id=adv_setting_id, intent=intent
        )

    kw = fetch_keyword_row(live_db_url, 2004)
    assert kw[2] == 9
    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert row[1] == CardAbHoldPhase.WB_SYNC.value
    assert list(row[12]) == ["alpha"]


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_setup_mutations_epoch_managed_fail_off_skips_active(
    live_db_url: str,
) -> None:
    """epoch_managed: FAIL→OFF writes KeywordSetting; AdvSetting mode stays PENDING."""
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=105,
        adv_id=9105,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.WARM_UP.value,
    )
    insert_keyword_row(
        live_db_url,
        keyword_id=2005,
        adv_setting_id=adv_setting_id,
        text_value="fail-kw",
        hard_status=2,
        strategy_mode="MIN_CPA",
        target_place=11,
    )
    insert_keyword_row(
        live_db_url,
        keyword_id=2006,
        adv_setting_id=adv_setting_id,
        text_value="pass-kw",
        hard_status=2,
        strategy_mode="MIN_CPA",
        target_place=3,
    )
    fail_kw = SimpleNamespace(
        keyword_setting_original_id=2005,
        text="fail-kw",
        views=50,
        pay_for_order=150.0,
        position=12.0,
    )
    pass_kw = SimpleNamespace(
        keyword_setting_original_id=2006,
        text="pass-kw",
        views=200,
        pay_for_order=40.0,
        position=8.0,
    )
    async with patched_async_session_maker(live_db_url):
        pass_count, fail_count = await apply_ab_hold_setup_mutations(
            adv_id=9105,
            adv_setting_id=adv_setting_id,
            keywords=[fail_kw, pass_kw],  # type: ignore[arg-type]
            max_pay_for_order=100.0,
            allowed_phrases_snapshot=["pass-kw"],
            epoch_managed=True,
        )

    assert (pass_count, fail_count) == (1, 1)
    failed = fetch_keyword_row(live_db_url, 2005)
    assert failed[0] == 1  # hard_status auto/OFF path
    assert failed[1] == "OFF"
    assert failed[2] is None
    passed = fetch_keyword_row(live_db_url, 2006)
    assert passed[2] == 3  # TP untouched on epoch_managed PASS
    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert row[0] == CardAbHoldMode.PENDING_SETUP.value


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_disable_card_ab_hold_clears_mode_and_epoch(
    live_db_url: str,
) -> None:
    """``disable_card_ab_hold`` WRITE ``sm(read_only=False)`` → OFF + epoch clears."""
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=106,
        adv_id=9106,
        mode=CardAbHoldMode.ACTIVE.value,
        phase=CardAbHoldPhase.READY_ACTIVE.value,
        bot_active=True,
        extra={
            "card_ab_hold_generation": 2,
            "card_ab_hold_confirmed_keywords_json": ["alpha"],
            "card_ab_hold_pending_intent_json": {"generation": 2},
            "card_ab_hold_sync_status": CardAbHoldSyncStatus.COMPLETE.value,
            "card_ab_hold_allowed_phrases_snapshot": ["alpha"],
        },
    )
    query = MagicMock()
    callback = CardAbHoldDisable(adv_setting_original_id=adv_setting_id)
    redis_clear = AsyncMock()
    fake_cache = MagicMock(return_value=SimpleNamespace(clear=redis_clear))
    async with patched_async_session_maker(live_db_url):
        with (
            patch(f"{_HANDLERS}._notify_callback_user", new_callable=AsyncMock),
            patch(f"{_HANDLERS}._edit_screen", new_callable=AsyncMock),
            patch(f"{_HANDLERS}.CardAbHoldSignalRedisCache", fake_cache),
            patch(f"{_HANDLERS}.CardAbHoldCommonBidEnterResetRedisCache", fake_cache),
            patch(f"{_HANDLERS}.CardAbHoldSetupBlockRedisCache", fake_cache),
        ):
            await disable_card_ab_hold(query, callback)

    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert row[0] == CardAbHoldMode.OFF.value
    assert row[1] is None
    assert int(row[4]) == 0
    assert row[5] is None
    assert row[9] is None
    assert list(row[12]) == []


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_abort_epoch_to_off_clears_mode_and_epoch(
    live_db_url: str,
) -> None:
    """``_abort_epoch_to_off`` WRITE mode→OFF + ``clear_epoch_on_exit`` re-read."""
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=107,
        adv_id=9107,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM.value,
        bot_active=True,
        extra={
            "card_ab_hold_confirmed_keywords_json": ["alpha"],
            "card_ab_hold_generation": 1,
            "card_ab_hold_allowed_phrases_snapshot": ["alpha"],
        },
    )
    adv = SimpleNamespace(id=adv_setting_id, adv_id=9107)
    redis_clear = AsyncMock()
    fake_cache = MagicMock(return_value=SimpleNamespace(clear=redis_clear))
    async with patched_async_session_maker(live_db_url):
        with (
            patch(f"{_CONFIRM}.CardAbHoldSignalRedisCache", fake_cache),
            patch(f"{_CONFIRM}.CardAbHoldSetupBlockRedisCache", fake_cache),
        ):
            await _abort_epoch_to_off(adv)  # type: ignore[arg-type]

    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert row[0] == CardAbHoldMode.OFF.value
    assert row[1] is None
    assert int(row[4]) == 0
    assert row[5] is None
    assert list(row[12]) == []


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_in_session_children_persist_via_injected_session(
    live_db_url: str,
) -> None:
    """Child ``*_in_session`` helpers принимают live session и пишут durable state."""
    adv_setting_id = insert_adv_row(
        live_db_url, adv_setting_id=108, adv_id=9108, mode="off", phase=None
    )
    insert_keyword_row(
        live_db_url,
        keyword_id=2108,
        adv_setting_id=adv_setting_id,
        text_value="gamma",
        target_place=None,
    )
    async with patched_async_session_maker(live_db_url):
        # Import sm *inside* the patch: module-level ``from … import sm`` would
        # keep the production session maker and miss disposable search_path.
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write import (
            sm as epoch_sm,
        )
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_handlers import (
            sm as confirm_sm,
        )
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.handlers import (
            sm as handlers_sm,
        )

        async with epoch_sm(read_only=False) as session:
            await start_epoch_on_enable_in_session(
                session, adv_setting_id, epoch_managed=True
            )
        async with epoch_sm(read_only=False) as session:
            await apply_confirmed_intent_to_pg_in_session(
                session,
                adv_setting_id=adv_setting_id,
                intent={
                    "keywords": ["gamma"],
                    "target_places": {"gamma": 4},
                    "generation": 1,
                },
            )
        async with confirm_sm(read_only=True) as session:
            loaded = await _load_adv_in_session(session, adv_setting_id)
        async with handlers_sm(read_only=True) as session:
            menu_adv = await load_adv_setting_for_ab_hold_menu(session, adv_setting_id)
            back_adv = await load_adv_setting_for_back(session, adv_setting_id)

    assert loaded is not None
    assert int(loaded.id) == adv_setting_id
    assert menu_adv is not None
    assert back_adv is not None
    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert row[0] == CardAbHoldMode.PENDING_SETUP.value
    assert row[1] == CardAbHoldPhase.WB_SYNC.value
    assert list(row[12]) == ["gamma"]
    kw = fetch_keyword_row(live_db_url, 2108)
    assert kw[2] == 4


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_back_load_adv_setting_for_menu_path(
    live_db_url: str,
) -> None:
    """``load_adv_setting_for_back`` PURE_READ re-select AdvSetting (+ cabinet join)."""
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=109,
        adv_id=9109,
        mode=CardAbHoldMode.ACTIVE.value,
        phase=CardAbHoldPhase.READY_ACTIVE.value,
        bot_active=True,
    )
    async with patched_async_session_maker(live_db_url):
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.handlers import (
            sm as handlers_sm,
        )

        async with handlers_sm(read_only=True) as session:
            adv = await load_adv_setting_for_back(session, adv_setting_id)

    assert adv is not None
    assert int(adv.id) == adv_setting_id
    assert int(adv.adv_id) == 9109


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_load_adv_setting_for_enable_gates_pure_read(
    live_db_url: str,
) -> None:
    """``load_adv_setting_for_enable_gates`` PURE_READ injected session + SQL re-read.

    Parent enable path opens ``sm(read_only=True)`` and hands session to this child;
    evidence is ORM load matching durable ``advsetting`` row (not session AsyncMock).
    """
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=112,
        adv_id=9112,
        mode=CardAbHoldMode.OFF.value,
        phase=None,
        bot_active=True,
    )
    async with patched_async_session_maker(live_db_url):
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.handlers import (
            sm as handlers_sm,
        )

        async with handlers_sm(read_only=True) as session:
            adv = await load_adv_setting_for_enable_gates(session, adv_setting_id)

    assert adv is not None
    assert int(adv.id) == adv_setting_id
    assert int(adv.adv_id) == 9112
    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert row[0] == CardAbHoldMode.OFF.value
    assert getattr(adv, "card_ab_hold_mode", None) == row[0]
    assert row[1] is None


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_load_adv_setting_after_enable_read_after_write(
    live_db_url: str,
) -> None:
    """``load_adv_setting_after_enable`` READ_AFTER_WRITE after durable enable write.

    Mirrors production: ``start_epoch_on_enable`` then child load under
    ``sm(read_only=False)``; SQL re-read proves PENDING_SETUP / AWAITING_KEYWORD.
    """
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=113,
        adv_id=9113,
        mode=CardAbHoldMode.OFF.value,
        phase=None,
        bot_active=True,
    )
    async with patched_async_session_maker(live_db_url):
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.handlers import (
            sm as handlers_sm,
        )

        with patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_write.can_enter_epoch_managed_ab_hold",
            return_value=True,
        ):
            managed = await start_epoch_on_enable(adv_setting_id, adv_id=9113)
        assert managed is True

        async with handlers_sm(read_only=False) as session:
            adv = await load_adv_setting_after_enable(session, adv_setting_id)

    assert adv is not None
    assert int(adv.id) == adv_setting_id
    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert row[0] == CardAbHoldMode.PENDING_SETUP.value
    assert row[1] == CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM.value
    assert getattr(adv, "card_ab_hold_mode", None) == row[0]
    assert getattr(adv, "card_ab_hold_phase", None) == row[1]


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_persist_ab_hold_degraded_flag_write_and_clear(
    live_db_url: str,
) -> None:
    """``persist_ab_hold_degraded_flag`` WRITE ``sm(read_only=False)`` + SQL re-read.

    Parent → ``persist_ab_hold_degraded_flag_in_session``; self-heal False clears
    the durable flag after True.
    """
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=110,
        adv_id=9110,
        mode=CardAbHoldMode.ACTIVE.value,
        phase=CardAbHoldPhase.READY_ACTIVE.value,
        bot_active=True,
    )
    assert fetch_adv_degraded_flag(live_db_url, adv_setting_id) is False

    async with patched_async_session_maker(live_db_url):
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_apply import (
            sm as setup_apply_sm,
        )

        await persist_ab_hold_degraded_flag(
            adv_setting_id=adv_setting_id, degraded=True
        )
        assert fetch_adv_degraded_flag(live_db_url, adv_setting_id) is True

        async with setup_apply_sm(read_only=False) as session:
            await persist_ab_hold_degraded_flag_in_session(
                session, adv_setting_id=adv_setting_id, degraded=False
            )
        assert fetch_adv_degraded_flag(live_db_url, adv_setting_id) is False

        await persist_ab_hold_degraded_flag(
            adv_setting_id=adv_setting_id, degraded=False
        )
    assert fetch_adv_degraded_flag(live_db_url, adv_setting_id) is False


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_apply_ab_hold_pfo_recovery_ons_persists_return_on(
    live_db_url: str,
) -> None:
    """``apply_ab_hold_pfo_recovery_ons`` WRITE seam + SQL re-read (A_PRIME).

    Parent ``sm(read_only=False)`` → ``apply_ab_hold_pfo_recovery_ons_in_session``;
    keyword was latched OFF → durable MIN_CPA + white-list hard_status.
    """
    from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
        hard_status_for_strategy_mode,
    )

    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=111,
        adv_id=9111,
        mode=CardAbHoldMode.ACTIVE.value,
        phase=CardAbHoldPhase.READY_ACTIVE.value,
        bot_active=True,
    )
    keyword_id = insert_keyword_row(
        live_db_url,
        keyword_id=2111,
        adv_setting_id=adv_setting_id,
        text_value="pfo-recovered",
        hard_status=hard_status_for_strategy_mode(KeywordStrategyMode.OFF),
        strategy_mode=KeywordStrategyMode.OFF.name,
        target_place=None,
    )
    before = fetch_keyword_row(live_db_url, keyword_id)
    assert before[0] == hard_status_for_strategy_mode(KeywordStrategyMode.OFF)
    assert before[1] == KeywordStrategyMode.OFF.name

    async with patched_async_session_maker(live_db_url):
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.hold_guards import (
            sm as hold_guards_sm,
        )

        updated = await apply_ab_hold_pfo_recovery_ons(
            adv_id=9111, keyword_ids=[keyword_id]
        )
        assert updated == 1
        after_parent = fetch_keyword_row(live_db_url, keyword_id)
        assert after_parent[0] == hard_status_for_strategy_mode(
            KeywordStrategyMode.MIN_CPA
        )
        assert after_parent[1] == KeywordStrategyMode.MIN_CPA.name

        # Reset latch, then prove injectable child seam with live session.
        insert_keyword_row(
            live_db_url,
            keyword_id=keyword_id,
            adv_setting_id=adv_setting_id,
            text_value="pfo-recovered",
            hard_status=hard_status_for_strategy_mode(KeywordStrategyMode.OFF),
            strategy_mode=KeywordStrategyMode.OFF.name,
            target_place=None,
        )
        async with hold_guards_sm(read_only=False) as session:
            child_updated = await apply_ab_hold_pfo_recovery_ons_in_session(
                session, keyword_ids=[keyword_id]
            )
        assert child_updated == 1

    after_child = fetch_keyword_row(live_db_url, keyword_id)
    assert after_child[0] == hard_status_for_strategy_mode(KeywordStrategyMode.MIN_CPA)
    assert after_child[1] == KeywordStrategyMode.MIN_CPA.name
    assert after_child[2] is None


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_apply_ab_hold_overspend_offs_clears_target_place(
    live_db_url: str,
) -> None:
    """``apply_ab_hold_overspend_offs`` WRITE seam + SQL re-read (FORCE_OFF).

    Parent ``sm(read_only=False)`` → ``apply_ab_hold_overspend_offs_in_session``;
    durable OFF hard_status / strategy_mode + ``target_place=None``.
    """
    from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
        hard_status_for_strategy_mode,
    )

    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=112,
        adv_id=9112,
        mode=CardAbHoldMode.ACTIVE.value,
        phase=CardAbHoldPhase.READY_ACTIVE.value,
        bot_active=True,
    )
    keyword_id = insert_keyword_row(
        live_db_url,
        keyword_id=2112,
        adv_setting_id=adv_setting_id,
        text_value="overspend-off",
        hard_status=hard_status_for_strategy_mode(KeywordStrategyMode.MIN_CPA),
        strategy_mode=KeywordStrategyMode.MIN_CPA.name,
        target_place=7,
    )
    before = fetch_keyword_row(live_db_url, keyword_id)
    assert before[2] == 7

    async with patched_async_session_maker(live_db_url):
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.hold_guards import (
            sm as hold_guards_sm,
        )

        updated = await apply_ab_hold_overspend_offs(
            adv_id=9112, keyword_ids=[keyword_id]
        )
        assert updated == 1
        after_parent = fetch_keyword_row(live_db_url, keyword_id)
        assert after_parent[0] == hard_status_for_strategy_mode(KeywordStrategyMode.OFF)
        assert after_parent[1] == KeywordStrategyMode.OFF.name
        assert after_parent[2] is None

        insert_keyword_row(
            live_db_url,
            keyword_id=keyword_id,
            adv_setting_id=adv_setting_id,
            text_value="overspend-off",
            hard_status=hard_status_for_strategy_mode(KeywordStrategyMode.MIN_CPA),
            strategy_mode=KeywordStrategyMode.MIN_CPA.name,
            target_place=5,
        )
        async with hold_guards_sm(read_only=False) as session:
            child_updated = await apply_ab_hold_overspend_offs_in_session(
                session, keyword_ids=[keyword_id]
            )
        assert child_updated == 1

    after_child = fetch_keyword_row(live_db_url, keyword_id)
    assert after_child[0] == hard_status_for_strategy_mode(KeywordStrategyMode.OFF)
    assert after_child[1] == KeywordStrategyMode.OFF.name
    assert after_child[2] is None
