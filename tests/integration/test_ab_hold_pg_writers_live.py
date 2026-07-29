"""Live PG re-read coverage for A/B Hold writers (external-call PG gaps).

Requires ``TEST_DATABASE_URL``. Proves durable writes via production ``sm`` seam
(patched to disposable DB) + SQL re-select — not session AsyncMock.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    CardAbHoldSyncStatus,
    DEFAULT_WARMUP_HOURS,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_pipelines import (
    apply_confirmed_intent_to_pg,
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
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_apply import (
    apply_ab_hold_setup_mutations,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldDisable,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_handlers import (
    _abort_epoch_to_off,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.handlers import (
    disable_card_ab_hold,
)
from tests.unit.auto_updater_v3.card_ab_hold._live_pg_bootstrap import (
    ensure_post_epoch_schema_for_orm,
    fetch_adv_epoch_row,
    fetch_keyword_row,
    insert_adv_row,
    insert_keyword_row,
    patched_async_session_maker,
)

_HAS_LIVE_PG = bool(os.getenv("TEST_DATABASE_URL"))
_HANDLERS = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.telegram.handlers"
)
_CONFIRM = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.telegram.confirm_handlers"
)


@pytest.fixture(scope="module")
def live_db_url() -> str:
    """Один disposable schema на модуль (требует TEST_DATABASE_URL)."""
    if not _HAS_LIVE_PG:
        pytest.skip("TEST_DATABASE_URL not set")
    db_url = os.environ["TEST_DATABASE_URL"]
    ensure_post_epoch_schema_for_orm(db_url)
    return db_url


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_LIVE_PG, reason="TEST_DATABASE_URL not set")
async def test_live_pg_start_epoch_on_enable_persists_mode_phase(
    live_db_url: str,
) -> None:
    """``start_epoch_on_enable`` → PENDING_SETUP + AWAITING_KEYWORD_CONFIRM."""
    adv_setting_id = insert_adv_row(
        live_db_url, adv_setting_id=101, adv_id=9101, mode="off", phase=None
    )
    with (
        patched_async_session_maker(live_db_url),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_write.can_enter_epoch_managed_ab_hold",
            return_value=True,
        ),
    ):
        managed = await start_epoch_on_enable(adv_setting_id, adv_id=9101)

    assert managed is True
    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert row[0] == CardAbHoldMode.PENDING_SETUP.value
    assert row[1] == CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM.value


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_LIVE_PG, reason="TEST_DATABASE_URL not set")
async def test_live_pg_warmup_keyword_and_duration_writers(live_db_url: str) -> None:
    """``confirm_keyword_set`` + ``set_warmup_duration`` durable WARM_UP timer."""
    adv_setting_id = insert_adv_row(
        live_db_url,
        adv_setting_id=102,
        adv_id=9102,
        mode=CardAbHoldMode.PENDING_SETUP.value,
        phase=CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM.value,
    )
    with patched_async_session_maker(live_db_url):
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


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_LIVE_PG, reason="TEST_DATABASE_URL not set")
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
    with patched_async_session_maker(live_db_url):
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


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_LIVE_PG, reason="TEST_DATABASE_URL not set")
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
    with patched_async_session_maker(live_db_url):
        await apply_confirmed_intent_to_pg(
            adv_setting_id=adv_setting_id, intent=intent
        )

    kw = fetch_keyword_row(live_db_url, 2004)
    assert kw[2] == 9
    row = fetch_adv_epoch_row(live_db_url, adv_setting_id)
    assert row[1] == CardAbHoldPhase.WB_SYNC.value
    assert list(row[12]) == ["alpha"]


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_LIVE_PG, reason="TEST_DATABASE_URL not set")
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
    with patched_async_session_maker(live_db_url):
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


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_LIVE_PG, reason="TEST_DATABASE_URL not set")
async def test_live_pg_disable_card_ab_hold_clears_mode_and_epoch(
    live_db_url: str,
) -> None:
    """``disable_card_ab_hold`` bare ``sm()`` WRITE → OFF + epoch clears (re-read)."""
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
    with (
        patched_async_session_maker(live_db_url),
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


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_LIVE_PG, reason="TEST_DATABASE_URL not set")
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
    with (
        patched_async_session_maker(live_db_url),
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
