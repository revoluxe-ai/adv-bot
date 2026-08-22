"""Mock-only regression: A/B Hold PG parent→child session handoff seams.

Доказывает injectable ``*_in_session`` / load helpers: parent открывает ``sm``,
передаёт ту же session в child. Не live PG (durable writes — integration suite).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold import (
    epoch_pipelines,
    epoch_write,
    hold_guards,
    setup_apply,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    CardAbHoldSyncStatus,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    confirm_handlers,
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldBack,
    CardAbHoldCancel,
    CardAbHoldDisable,
    CardAbHoldEnable,
    CardAbHoldMenu,
)


def _session_cm(fake_session: Any) -> MagicMock:
    """Async context manager yielding ``fake_session``."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


def _assert_child_got_session(
    child: AsyncMock,
    fake_session: Any,
    *,
    read_only: bool,
    sm_mock: MagicMock,
) -> None:
    """Parent MUST open sm(read_only=…) and await child with that session first."""
    sm_mock.assert_called_with(read_only=read_only)
    child.assert_awaited()
    assert child.await_args is not None
    assert child.await_args.args[0] is fake_session


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("parent_name", "child_name", "call"),
    [
        (
            "start_epoch_on_enable",
            "start_epoch_on_enable_in_session",
            lambda: epoch_write.start_epoch_on_enable(1, adv_id=10, shop_id=1),
        ),
        (
            "confirm_keyword_set_and_start_warmup",
            "confirm_keyword_set_and_start_warmup_in_session",
            lambda: epoch_write.confirm_keyword_set_and_start_warmup(1, ["kw"]),
        ),
        (
            "set_warmup_duration",
            "set_warmup_duration_in_session",
            lambda: epoch_write.set_warmup_duration(1, 24),
        ),
        (
            "advance_warmup_to_tp_confirm",
            "advance_warmup_to_tp_confirm_in_session",
            lambda: epoch_write.advance_warmup_to_tp_confirm(1),
        ),
        (
            "confirm_target_places",
            "confirm_target_places_in_session",
            lambda: epoch_write.confirm_target_places(1, {"kw": 5}),
        ),
        (
            "confirm_auto_participation",
            "confirm_auto_participation_in_session",
            lambda: epoch_write.confirm_auto_participation(1, True),
        ),
        (
            "create_pending_intent_for_generation",
            "create_pending_intent_for_generation_in_session",
            lambda: epoch_write.create_pending_intent_for_generation(1, adv_id=10),
        ),
        (
            "mark_wb_sync_status",
            "mark_wb_sync_status_in_session",
            lambda: epoch_write.mark_wb_sync_status(
                1, CardAbHoldSyncStatus.COMPLETE
            ),
        ),
        (
            "activate_after_successful_sync",
            "activate_after_successful_sync_in_session",
            lambda: epoch_write.activate_after_successful_sync(1),
        ),
        (
            "clear_epoch_on_exit",
            "clear_epoch_on_exit_in_session",
            lambda: epoch_write.clear_epoch_on_exit(1),
        ),
    ],
)
async def test_epoch_write_parents_hand_off_session_to_in_session_children(
    parent_name: str,
    child_name: str,
    call: Any,
) -> None:
    """Каждый public WRITE parent открывает sm(read_only=False) и зовёт *_in_session."""
    _ = parent_name
    fake_session = MagicMock(name="epoch_write_session")
    child = AsyncMock(return_value=True)
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    with (
        patch.object(epoch_write, "sm", sm_mock),
        patch.object(epoch_write, child_name, child),
        patch.object(
            epoch_write,
            "can_enter_epoch_managed_ab_hold",
            return_value=True,
        ),
    ):
        await call()
    _assert_child_got_session(
        child, fake_session, read_only=False, sm_mock=sm_mock
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confirm_auto_bid_hands_off_session_then_creates_intent() -> None:
    """``confirm_auto_bid`` → ``*_in_session`` with WRITE session, then intent parent."""
    fake_session = MagicMock(name="confirm_auto_bid_session")
    child = AsyncMock(return_value=99)
    intent = AsyncMock(return_value=True)
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    with (
        patch.object(epoch_write, "sm", sm_mock),
        patch.object(epoch_write, "confirm_auto_bid_in_session", child),
        patch.object(epoch_write, "create_pending_intent_for_generation", intent),
    ):
        await epoch_write.confirm_auto_bid(1, 12.5)
    _assert_child_got_session(
        child, fake_session, read_only=False, sm_mock=sm_mock
    )
    intent.assert_awaited_once_with(1, adv_id=99)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_apply_and_intent_parents_hand_off_session() -> None:
    """setup_apply / apply_confirmed_intent parents → *_in_session children."""
    fake_session = MagicMock(name="setup_session")
    setup_child = AsyncMock()
    degraded_child = AsyncMock()
    intent_child = AsyncMock()
    setup_sm = MagicMock(return_value=_session_cm(fake_session))
    intent_sm = MagicMock(return_value=_session_cm(fake_session))

    with (
        patch.object(setup_apply, "sm", setup_sm),
        patch.object(
            setup_apply, "apply_ab_hold_setup_mutations_in_session", setup_child
        ),
    ):
        await setup_apply.apply_ab_hold_setup_mutations(
            adv_id=10,
            adv_setting_id=20,
            keywords=[],
            max_pay_for_order=100.0,
            epoch_managed=True,
        )
    _assert_child_got_session(
        setup_child, fake_session, read_only=False, sm_mock=setup_sm
    )

    with (
        patch.object(setup_apply, "sm", setup_sm),
        patch.object(
            setup_apply, "persist_ab_hold_degraded_flag_in_session", degraded_child
        ),
    ):
        await setup_apply.persist_ab_hold_degraded_flag(
            adv_setting_id=20, degraded=True
        )
    _assert_child_got_session(
        degraded_child, fake_session, read_only=False, sm_mock=setup_sm
    )

    with (
        patch.object(epoch_pipelines, "sm", intent_sm),
        patch.object(
            epoch_pipelines,
            "apply_confirmed_intent_to_pg_in_session",
            intent_child,
        ),
    ):
        await epoch_pipelines.apply_confirmed_intent_to_pg(
            adv_setting_id=20,
            intent={"keywords": ["kw"], "target_places": {"kw": 1}},
        )
    _assert_child_got_session(
        intent_child, fake_session, read_only=False, sm_mock=intent_sm
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hold_guards_pfo_recovery_parent_hands_off_session() -> None:
    """``apply_ab_hold_pfo_recovery_ons`` → ``*_in_session`` + sm(read_only=False)."""
    fake_session = MagicMock(name="pfo_session")
    child = AsyncMock(return_value=2)
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    with (
        patch.object(hold_guards, "sm", sm_mock),
        patch.object(
            hold_guards, "apply_ab_hold_pfo_recovery_ons_in_session", child
        ),
    ):
        updated = await hold_guards.apply_ab_hold_pfo_recovery_ons(
            adv_id=10, keyword_ids=[1, 2]
        )
    assert updated == 2
    _assert_child_got_session(
        child, fake_session, read_only=False, sm_mock=sm_mock
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hold_guards_overspend_offs_parent_hands_off_session() -> None:
    """``apply_ab_hold_overspend_offs`` → ``*_in_session`` + sm(read_only=False)."""
    fake_session = MagicMock(name="overspend_session")
    child = AsyncMock(return_value=3)
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    with (
        patch.object(hold_guards, "sm", sm_mock),
        patch.object(
            hold_guards, "apply_ab_hold_overspend_offs_in_session", child
        ),
    ):
        updated = await hold_guards.apply_ab_hold_overspend_offs(
            adv_id=10, keyword_ids=[1, 2, 3]
        )
    assert updated == 3
    _assert_child_got_session(
        child, fake_session, read_only=False, sm_mock=sm_mock
    )


def _query_stub() -> MagicMock:
    """Minimal CallbackQuery stub for Telegram parent handoff tests."""
    from aiogram.types import Message

    query = MagicMock()
    query.answer = AsyncMock()
    msg = MagicMock(spec=Message)
    msg.answer = AsyncMock()
    msg.chat = SimpleNamespace(id=1)
    msg.bot = MagicMock()
    msg.bot.send_message = AsyncMock()
    query.message = msg
    query.bot = msg.bot
    query.from_user = SimpleNamespace(id=7)
    return query


@pytest.mark.unit
@pytest.mark.asyncio
async def test_telegram_menu_cancel_disable_back_hand_off_session() -> None:
    """Telegram parents передают injectable session в load/write children."""
    fake_session = MagicMock(name="tg_session")
    adv = SimpleNamespace(
        id=42,
        adv_id=4242,
        bot_active=True,
        card_ab_hold_mode="off",
        card_ab_hold_phase=None,
        card_ab_hold_degraded=False,
        wb_cabinet=SimpleNamespace(shop_id="1"),
    )
    query = _query_stub()

    load_menu = AsyncMock(return_value=adv)
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    with (
        patch.object(handlers, "sm", sm_mock),
        patch.object(handlers, "load_adv_setting_for_ab_hold_menu", load_menu),
        patch.object(handlers, "_edit_screen", new_callable=AsyncMock),
        patch.object(
            handlers,
            "_screen_status_text",
            new_callable=AsyncMock,
            return_value="Статус: off",
        ),
        patch.object(handlers, "is_card_ab_hold_ui_visible", return_value=True),
    ):
        await handlers.open_card_ab_hold_menu(
            query, CardAbHoldMenu(adv_setting_original_id=42)
        )
    _assert_child_got_session(
        load_menu, fake_session, read_only=True, sm_mock=sm_mock
    )

    load_cancel = AsyncMock(return_value=adv)
    sm_cancel = MagicMock(return_value=_session_cm(fake_session))
    with (
        patch.object(handlers, "sm", sm_cancel),
        patch.object(handlers, "load_adv_setting_for_ab_hold_menu", load_cancel),
        patch.object(handlers, "_edit_screen", new_callable=AsyncMock),
        patch.object(handlers, "is_card_ab_hold_ui_visible", return_value=True),
    ):
        await handlers.cancel_card_ab_hold_enable(
            query, CardAbHoldCancel(adv_setting_original_id=42)
        )
    _assert_child_got_session(
        load_cancel, fake_session, read_only=True, sm_mock=sm_cancel
    )

    disable_child = AsyncMock(return_value=adv)
    sm_disable = MagicMock(return_value=_session_cm(fake_session))
    with (
        patch.object(handlers, "sm", sm_disable),
        patch.object(handlers, "disable_card_ab_hold_in_session", disable_child),
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(clear=AsyncMock()),
        ),
        patch.object(
            handlers,
            "CardAbHoldCommonBidEnterResetRedisCache",
            return_value=MagicMock(clear=AsyncMock()),
        ),
        patch.object(
            handlers,
            "CardAbHoldSetupBlockRedisCache",
            return_value=MagicMock(clear=AsyncMock()),
        ),
        patch.object(handlers, "_edit_screen", new_callable=AsyncMock),
    ):
        await handlers.disable_card_ab_hold(
            query, CardAbHoldDisable(adv_setting_original_id=42)
        )
    _assert_child_got_session(
        disable_child, fake_session, read_only=False, sm_mock=sm_disable
    )

    load_back = AsyncMock(return_value=adv)
    cab = AsyncMock(return_value=MagicMock())
    menu_cls = MagicMock(return_value=AsyncMock())
    sm_back = MagicMock(return_value=_session_cm(fake_session))
    with (
        patch.object(handlers, "sm", sm_back),
        patch.object(handlers, "load_adv_setting_for_back", load_back),
        patch.object(handlers, "get_wb_user_cabinet_for_adv_and_telegram", cab),
        patch.object(handlers, "_load_adv_setting_menu", return_value=menu_cls),
    ):
        await handlers.back_from_card_ab_hold(
            query, CardAbHoldBack(adv_setting_original_id=42)
        )
    _assert_child_got_session(
        load_back, fake_session, read_only=True, sm_mock=sm_back
    )
    cab.assert_awaited()
    assert cab.await_args is not None
    assert cab.await_args.args[0] is fake_session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_handler_hands_off_read_sessions_to_load_helpers() -> None:
    """``_handle_ab_hold_enable`` передаёт sm sessions в load_adv_setting_* helpers."""
    fake_gates = MagicMock(name="enable_gates_session")
    fake_after = MagicMock(name="enable_after_session")
    adv = SimpleNamespace(
        id=9,
        adv_id=99,
        bot_active=True,
        max_price_for_order=100.0,
        card_ab_hold_mode="off",
        card_ab_hold_degraded=False,
        wb_cabinet=SimpleNamespace(shop_id="1"),
        search_adv_id=None,
    )
    refreshed = SimpleNamespace(
        id=9,
        adv_id=99,
        bot_active=True,
        card_ab_hold_mode="pending_setup",
        card_ab_hold_degraded=False,
        card_ab_hold_phase=None,
    )
    load_gates = AsyncMock(return_value=adv)
    load_after = AsyncMock(return_value=refreshed)
    sm_mock = MagicMock(
        side_effect=[_session_cm(fake_gates), _session_cm(fake_after)]
    )
    query = _query_stub()
    with (
        patch.object(handlers, "sm", sm_mock),
        patch.object(handlers, "load_adv_setting_for_enable_gates", load_gates),
        patch.object(handlers, "load_adv_setting_after_enable", load_after),
        patch.object(
            handlers, "start_epoch_on_enable", AsyncMock(return_value=True)
        ),
        patch.object(
            handlers,
            "evaluate_ab_hold_enable_stats",
            new_callable=AsyncMock,
            return_value=(True, None),
        ),
        patch.object(
            handlers,
            "evaluate_ab_hold_launch_view_volume",
            new_callable=AsyncMock,
        ) as volume,
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(set_signal=AsyncMock()),
        ),
        patch.object(
            handlers,
            "CardAbHoldLastAbortRedisCache",
            return_value=MagicMock(get_abort=AsyncMock(return_value=None)),
        ),
        patch.object(handlers, "_edit_screen", new_callable=AsyncMock),
        patch.object(handlers, "can_enable_card_ab_hold", return_value=True),
    ):
        volume.return_value.is_unavailable = False
        volume.return_value.is_sufficient = True
        await handlers.enable_card_ab_hold(
            query, CardAbHoldEnable(adv_setting_original_id=9)
        )

    assert sm_mock.call_args_list[0].kwargs.get("read_only") is True
    assert load_gates.await_args is not None
    assert load_gates.await_args.args[0] is fake_gates
    assert load_after.await_args is not None
    assert load_after.await_args.args[0] is fake_after


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confirm_handlers_load_and_abort_hand_off_session() -> None:
    """confirm_handlers hand off one write session to both EXIT children."""
    fake_session = MagicMock(name="confirm_session")
    fake_session.commit = AsyncMock()
    load_child = AsyncMock(return_value=MagicMock(id=5))
    abort_child = AsyncMock(return_value=MagicMock(id=5))
    clear_epoch_child = AsyncMock()
    sm_load = MagicMock(return_value=_session_cm(fake_session))
    sm_abort = MagicMock(return_value=_session_cm(fake_session))

    with (
        patch.object(confirm_handlers, "sm", sm_load),
        patch.object(confirm_handlers, "_load_adv_in_session", load_child),
    ):
        await confirm_handlers._load_adv(5)
    _assert_child_got_session(
        load_child, fake_session, read_only=True, sm_mock=sm_load
    )

    adv = SimpleNamespace(id=5, adv_id=50)
    with (
        patch.object(confirm_handlers, "sm", sm_abort),
        patch.object(
            confirm_handlers, "_abort_epoch_mode_off_in_session", abort_child
        ),
        patch.object(
            confirm_handlers,
            "clear_epoch_on_exit_in_session",
            clear_epoch_child,
        ),
        patch.object(
            confirm_handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(clear=AsyncMock()),
        ),
        patch.object(
            confirm_handlers,
            "CardAbHoldSetupBlockRedisCache",
            return_value=MagicMock(clear=AsyncMock()),
        ),
    ):
        await confirm_handlers._abort_epoch_to_off(adv)  # type: ignore[arg-type]
    _assert_child_got_session(
        abort_child, fake_session, read_only=False, sm_mock=sm_abort
    )
    clear_epoch_child.assert_awaited_once()
    assert clear_epoch_child.await_args is not None
    assert clear_epoch_child.await_args.args[0] is fake_session
    assert clear_epoch_child.await_args.kwargs["commit"] is False
    fake_session.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_live_pg_bootstrap_awaits_async_engine_dispose() -> None:
    """``patched_async_session_maker`` MUST ``await engine.dispose()`` on exit."""
    from tests.integration.card_ab_hold import _live_pg_bootstrap as boot

    dispose = AsyncMock()
    engine = MagicMock()
    engine.dispose = dispose
    maker = MagicMock(return_value=MagicMock())

    @asynccontextmanager
    async def _unused_sm(*, read_only: bool = False):
        _ = read_only
        yield MagicMock()

    with (
        patch.object(boot, "create_validated_async_engine", return_value=engine),
        patch.object(boot, "async_sessionmaker", return_value=maker),
    ):
        async with boot.patched_async_session_maker(
            "postgresql+asyncpg://u:p@localhost/testdb",
            targets=(),
        ):
            pass
    dispose.assert_awaited_once()


@pytest.mark.unit
def test_live_pg_bootstrap_patches_hold_guards_sm() -> None:
    """Disposable schema patch MUST cover hold_guards.sm (PFO recovery writer)."""
    from tests.integration.card_ab_hold import _live_pg_bootstrap as boot

    assert any(
        target.endswith("hold_guards.sm") for target in boot._CARD_AB_HOLD_SM_TARGETS
    )


@pytest.mark.unit
def test_live_pg_bootstrap_fetch_adv_degraded_flag_reselects_column() -> None:
    """Shared re-read helper executes SELECT of ``card_ab_hold_degraded``."""
    from sqlalchemy.sql.elements import TextClause

    from tests.integration.card_ab_hold import _live_pg_bootstrap as boot

    executed: list[Any] = []
    conn = MagicMock()

    def _execute(stmt: Any, params: Any = None) -> MagicMock:
        executed.append((stmt, params))
        result = MagicMock()
        result.scalar_one = MagicMock(return_value=True)
        return result

    conn.execute = MagicMock(side_effect=_execute)
    engine = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
    engine.connect.return_value.__exit__ = MagicMock(return_value=None)
    engine.dispose = MagicMock()

    with patch.object(boot, "create_validated_sync_engine", return_value=engine):
        assert boot.fetch_adv_degraded_flag("postgresql://u:p@localhost/testdb", 7) is True

    assert executed, "fetch_adv_degraded_flag MUST execute a SELECT"
    stmt, params = executed[0]
    assert isinstance(stmt, TextClause)
    sql = str(stmt)
    assert "card_ab_hold_degraded" in sql
    assert "advsetting" in sql.lower()
    assert params == {"id": 7}


@pytest.mark.unit
def test_live_pg_bootstrap_wbcabinet_stub_covers_orm_joined_columns() -> None:
    """Stub ``wbcabinet`` MUST include WBCabinet mapped cols (lazy=joined AdvSetting).

    Regression: id-only stub → UndefinedColumn shop_id on ``_load_adv`` / menu-back.
    """
    from tests.integration.card_ab_hold import _live_pg_bootstrap as boot

    ddl = boot._PRE_EPOCH_DDL
    assert "CREATE TABLE wbcabinet" in ddl
    for col in (
        "shop_id",
        "active",
        "expiration_time",
        "balance",
        "bonus",
        "default_max_cpm",
        "balance_went_negative_at",
    ):
        assert col in ddl, f"missing ORM column in wbcabinet stub: {col}"
    assert "live_pg_stub_shop" in ddl


@pytest.mark.unit
def test_live_pg_bootstrap_post_epoch_schema_applies_emergency_for_orm() -> None:
    """ORM live bootstrap MUST apply emergency latch cols (mapped on AdvSetting).

    Regression: epoch-only disposable schema → UndefinedColumn
    ``card_ab_hold_emergency_latch`` on ``SELECT … FOR UPDATE``.
    """
    import inspect

    from tests.integration.card_ab_hold import _live_pg_bootstrap as boot

    src = inspect.getsource(boot.ensure_post_epoch_schema_for_orm)
    assert "ensure_emergency_latch_columns" in src
    alias_src = inspect.getsource(boot.ensure_post_epoch_with_emergency_schema_for_orm)
    assert "ensure_post_epoch_schema_for_orm" in alias_src
    assert "ensure_emergency_latch_columns" not in alias_src


@pytest.mark.unit
def test_live_pg_bootstrap_patches_emergency_handlers_sm() -> None:
    """Disposable schema patch MUST cover emergency_handlers.sm (educate WRITE)."""
    from tests.integration.card_ab_hold import _live_pg_bootstrap as boot

    assert any(
        target.endswith("emergency_handlers.sm")
        for target in boot._CARD_AB_HOLD_SM_TARGETS
    )


@pytest.mark.unit
def test_live_pg_bootstrap_fetch_emergency_educated_flag_reselects_column() -> None:
    """Shared re-read helper executes SELECT of ``card_ab_hold_emergency_educated``."""
    from sqlalchemy.sql.elements import TextClause

    from tests.integration.card_ab_hold import _live_pg_bootstrap as boot

    executed: list[Any] = []
    conn = MagicMock()

    def _execute(stmt: Any, params: Any = None) -> MagicMock:
        executed.append((stmt, params))
        result = MagicMock()
        result.scalar_one = MagicMock(return_value=True)
        return result

    conn.execute = MagicMock(side_effect=_execute)
    engine = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
    engine.connect.return_value.__exit__ = MagicMock(return_value=None)
    engine.dispose = MagicMock()

    with patch.object(boot, "create_validated_sync_engine", return_value=engine):
        assert (
            boot.fetch_emergency_educated_flag(
                "postgresql://u:p@localhost/testdb", 77
            )
            is True
        )

    assert executed, "fetch_emergency_educated_flag MUST execute a SELECT"
    stmt, params = executed[0]
    assert isinstance(stmt, TextClause)
    sql = str(stmt)
    assert "card_ab_hold_emergency_educated" in sql
    assert "advsetting" in sql.lower()
    assert params == {"id": 77}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_emergency_educate_ack_hands_off_write_session_to_in_session_child() -> None:
    """``emergency_educate_ack`` → ``acknowledge_emergency_education_in_session``."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
        emergency_handlers,
        handlers,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
        CardAbHoldEmergencyEducate,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.emergency_handlers import (
        EmergencyEducateAckOutcome,
    )

    fake_session = MagicMock(name="emergency_educate_session")
    fake_session.commit = AsyncMock()
    adv = SimpleNamespace(
        id=77,
        card_ab_hold_mode="active",
        card_ab_hold_phase=None,
        card_ab_hold_emergency_latch=False,
    )
    child = AsyncMock(
        return_value=EmergencyEducateAckOutcome(kind="ok", adv=adv)
    )
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    with (
        patch.object(emergency_handlers, "sm", sm_mock),
        patch.object(
            emergency_handlers, "acknowledge_emergency_education_in_session", child
        ),
        patch.object(
            handlers, "_screen_status_text", AsyncMock(return_value="Статус: active")
        ),
        patch.object(handlers, "_notify_callback_user", AsyncMock()),
        patch.object(handlers, "_edit_screen", AsyncMock()),
    ):
        query = MagicMock()
        cb = CardAbHoldEmergencyEducate(adv_setting_original_id=77)
        await emergency_handlers.emergency_educate_ack(query, cb)

    _assert_child_got_session(
        child, fake_session, read_only=False, sm_mock=sm_mock
    )
    fake_session.commit.assert_awaited()
    assert child.await_args is not None
    assert child.await_args.kwargs["adv_setting_original_id"] == 77


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acknowledge_emergency_education_in_session_marks_educated() -> None:
    """Child seam: UI visible + Hold mode → mark educated on AdvSetting."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
        CardAbHoldMode,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
        emergency_handlers,
    )

    adv = SimpleNamespace(
        id=77,
        bot_active=True,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        card_ab_hold_emergency_educated=False,
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=adv)

    outcome = await emergency_handlers.acknowledge_emergency_education_in_session(
        session, adv_setting_original_id=77
    )

    assert outcome.kind == "ok"
    assert outcome.adv is adv
    assert adv.card_ab_hold_emergency_educated is True
    session.get.assert_awaited_once()
