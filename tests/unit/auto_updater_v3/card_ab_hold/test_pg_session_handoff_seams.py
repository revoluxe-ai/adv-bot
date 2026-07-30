"""Mock-only regression: A/B Hold PG parent→child session handoff seams.

Доказывает injectable ``*_in_session`` / load helpers и корректный
``read_only=`` у parent orchestration. Не live PG.
"""

from __future__ import annotations

import inspect

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold import (
    epoch_pipelines,
    epoch_write,
    setup_apply,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    confirm_handlers,
    handlers,
)


@pytest.mark.unit
def test_epoch_write_parents_hand_off_session_to_in_session_children() -> None:
    """Каждый public WRITE parent открывает sm(read_only=False) и зовёт *_in_session."""
    pairs = (
        (epoch_write.start_epoch_on_enable, "start_epoch_on_enable_in_session"),
        (
            epoch_write.confirm_keyword_set_and_start_warmup,
            "confirm_keyword_set_and_start_warmup_in_session",
        ),
        (epoch_write.set_warmup_duration, "set_warmup_duration_in_session"),
        (
            epoch_write.advance_warmup_to_tp_confirm,
            "advance_warmup_to_tp_confirm_in_session",
        ),
        (epoch_write.confirm_target_places, "confirm_target_places_in_session"),
        (
            epoch_write.confirm_auto_participation,
            "confirm_auto_participation_in_session",
        ),
        (epoch_write.confirm_auto_bid, "confirm_auto_bid_in_session"),
        (
            epoch_write.create_pending_intent_for_generation,
            "create_pending_intent_for_generation_in_session",
        ),
        (epoch_write.mark_wb_sync_status, "mark_wb_sync_status_in_session"),
        (
            epoch_write.activate_after_successful_sync,
            "activate_after_successful_sync_in_session",
        ),
        (epoch_write.clear_epoch_on_exit, "clear_epoch_on_exit_in_session"),
    )
    for parent, child_name in pairs:
        src = inspect.getsource(parent)
        assert "sm(read_only=False)" in src, parent.__name__
        assert child_name in src, parent.__name__
        child = getattr(epoch_write, child_name)
        assert "session" in inspect.signature(child).parameters


@pytest.mark.unit
def test_setup_apply_and_intent_parents_hand_off_session() -> None:
    """setup_apply / apply_confirmed_intent parents → *_in_session children."""
    setup_src = inspect.getsource(setup_apply.apply_ab_hold_setup_mutations)
    assert "sm(read_only=False)" in setup_src
    assert "apply_ab_hold_setup_mutations_in_session" in setup_src
    assert "session" in inspect.signature(
        setup_apply.apply_ab_hold_setup_mutations_in_session
    ).parameters

    degraded_src = inspect.getsource(setup_apply.persist_ab_hold_degraded_flag)
    assert "sm(read_only=False)" in degraded_src
    assert "persist_ab_hold_degraded_flag_in_session" in degraded_src
    assert "session" in inspect.signature(
        setup_apply.persist_ab_hold_degraded_flag_in_session
    ).parameters

    intent_src = inspect.getsource(epoch_pipelines.apply_confirmed_intent_to_pg)
    assert "sm(read_only=False)" in intent_src
    assert "apply_confirmed_intent_to_pg_in_session" in intent_src
    assert "session" in inspect.signature(
        epoch_pipelines.apply_confirmed_intent_to_pg_in_session
    ).parameters


@pytest.mark.unit
def test_telegram_handlers_hand_off_session_to_load_or_write_children() -> None:
    """Telegram parents передают session в load/write child callables."""
    menu_src = inspect.getsource(handlers.open_card_ab_hold_menu)
    assert "sm(read_only=True)" in menu_src
    assert "load_adv_setting_for_ab_hold_menu" in menu_src

    enable_src = inspect.getsource(handlers._handle_ab_hold_enable)
    assert "load_adv_setting_for_enable_gates" in enable_src
    assert "load_adv_setting_after_enable" in enable_src
    assert "sm(read_only=True)" in enable_src
    assert "sm(read_only=False)" in enable_src

    cancel_src = inspect.getsource(handlers.cancel_card_ab_hold_enable)
    assert "load_adv_setting_for_ab_hold_menu" in cancel_src
    assert "sm(read_only=True)" in cancel_src

    disable_src = inspect.getsource(handlers.disable_card_ab_hold)
    assert "disable_card_ab_hold_in_session" in disable_src
    assert "sm(read_only=False)" in disable_src

    back_src = inspect.getsource(handlers.back_from_card_ab_hold)
    assert "load_adv_setting_for_back" in back_src
    assert "sm(read_only=True)" in back_src
    assert "get_wb_user_cabinet_for_adv_and_telegram" in back_src

    for name in (
        "load_adv_setting_for_ab_hold_menu",
        "load_adv_setting_for_enable_gates",
        "load_adv_setting_after_enable",
        "disable_card_ab_hold_in_session",
        "load_adv_setting_for_back",
    ):
        assert "session" in inspect.signature(getattr(handlers, name)).parameters


@pytest.mark.unit
def test_confirm_handlers_load_and_abort_hand_off_session() -> None:
    """confirm_handlers _load_adv / abort → session children."""
    load_src = inspect.getsource(confirm_handlers._load_adv)
    assert "sm(read_only=True)" in load_src
    assert "_load_adv_in_session" in load_src

    abort_src = inspect.getsource(confirm_handlers._abort_epoch_to_off)
    assert "sm(read_only=False)" in abort_src
    assert "_abort_epoch_mode_off_in_session" in abort_src

    assert "session" in inspect.signature(
        confirm_handlers._load_adv_in_session
    ).parameters
    assert "session" in inspect.signature(
        confirm_handlers._abort_epoch_mode_off_in_session
    ).parameters


@pytest.mark.unit
def test_live_pg_bootstrap_awaits_async_engine_dispose() -> None:
    """Unsafe ``sync_engine.dispose()`` запрещён; нужен ``await engine.dispose()``."""
    from tests.integration.card_ab_hold import _live_pg_bootstrap as boot

    src = inspect.getsource(boot.patched_async_session_maker)
    assert "await engine.dispose()" in src
    assert "sync_engine.dispose" not in src
    assert "@asynccontextmanager" in inspect.getsource(boot)


@pytest.mark.unit
def test_live_pg_bootstrap_fetch_adv_degraded_flag_reselects_column() -> None:
    """Shared re-read helper для ``persist_ab_hold_degraded_flag`` live evidence."""
    from tests.integration.card_ab_hold import _live_pg_bootstrap as boot

    src = inspect.getsource(boot.fetch_adv_degraded_flag)
    assert "card_ab_hold_degraded" in src
    assert "advsetting" in src


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