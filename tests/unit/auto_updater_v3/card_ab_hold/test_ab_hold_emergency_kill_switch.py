"""Unit-тесты Emergency kill switch (spec ab-hold-emergency-kill-switch).

Проверяют visibility, latch gate, executor idempotency/partial, confirm cancel,
Telegram payload limits и activity-control force-pause при ACTIVE latch.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Awaitable, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.auto_budget_manager.service import (
    AutoBudgetEnsureStatus,
    AutoBudgetService,
)
from app.modules.shop_runner.service_manager.services.auto_adv_active_control import (
    AutoAdvActiveControlService,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.emergency import (
    SUPPORT_LINK,
    EmergencyApplyResult,
    apply_ab_hold_emergency_in_session,
    format_emergency_user_result_text,
    is_ab_hold_emergency_latch_active,
    is_ab_hold_emergency_visible,
    is_emergency_educated,
    should_suppress_budget_and_activity_restart,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    emergency_handlers,
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldEmergencyAbort,
    CardAbHoldEmergencyAsk,
    CardAbHoldEmergencyConfirm,
    CardAbHoldEmergencyEducate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.emergency_handlers import (
    EmergencyEducateAckOutcome,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.handlers import (
    _screen_keyboard,
)
from app.shared.domains.wb.enums import AdvType

pytestmark = pytest.mark.unit

_TG_MESSAGE_TEXT_MAX = 4096
_TG_CALLBACK_DATA_BYTES_MAX = 64
_TG_CALLBACK_ANSWER_MAX = 200
_WORST_CASE_ADV_SETTING_ID = 2_147_483_647

_ACTIVITY_MODULE = (
    "app.modules.shop_runner.service_manager.services.auto_adv_active_control"
    ".auto_adv_active_control_service"
)


def test_emergency_hidden_when_hold_off() -> None:
    """Spec: Emergency control visible only under A/B Hold — OFF hides."""
    assert is_ab_hold_emergency_visible(CardAbHoldMode.OFF) is False
    assert is_ab_hold_emergency_visible("off") is False
    kb = _screen_keyboard(1, CardAbHoldMode.OFF, emergency_educated=True)
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert all("Emergency" not in (t or "") for t in texts)


def test_emergency_visible_when_hold_non_off() -> None:
    """Spec: Hold non-OFF shows Emergency (после education ACK)."""
    assert is_ab_hold_emergency_visible(CardAbHoldMode.ACTIVE) is True
    assert is_ab_hold_emergency_visible(CardAbHoldMode.PENDING_SETUP) is True
    kb = _screen_keyboard(
        1, CardAbHoldMode.ACTIVE, emergency_educated=True, emergency_latch=False
    )
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert any("Emergency" in (t or "") for t in texts)


def test_emergency_education_gate_before_button() -> None:
    """Spec: Launch education — без ACK кнопка Emergency заменена на educate."""
    kb = _screen_keyboard(
        1, CardAbHoldMode.ACTIVE, emergency_educated=False, emergency_latch=False
    )
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert any("прочитать" in (t or "").lower() for t in texts)
    assert not any(t == "🚨 Emergency — остановить траты" for t in texts)


def test_emergency_latch_shows_support_url() -> None:
    """Spec: Immediate support contact — при latch кнопка URL на SUPPORT_LINK."""
    kb = _screen_keyboard(
        1, CardAbHoldMode.ACTIVE, emergency_educated=True, emergency_latch=True
    )
    urls = [btn.url for row in kb.inline_keyboard for btn in row if btn.url]
    assert SUPPORT_LINK in urls
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert not any("снять" in (t or "").lower() and "авари" in (t or "").lower() for t in texts)
    assert not any("сброс" in (t or "").lower() for t in texts)


def test_latch_suppresses_budget_and_restart() -> None:
    """Spec: Activity control respects latch / paired positive OFF."""
    assert should_suppress_budget_and_activity_restart(True) is True
    assert should_suppress_budget_and_activity_restart(False) is False
    assert is_ab_hold_emergency_latch_active(True) is True
    assert is_emergency_educated(True) is True
    assert is_emergency_educated(False) is False


@pytest.mark.asyncio
async def test_apply_emergency_sets_latch_keeps_hold_mode() -> None:
    """Spec: Emergency stops spend — latch ON, Hold mode не → OFF."""
    adv = SimpleNamespace(
        id=42,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        card_ab_hold_emergency_latch=False,
        auto_adv_target_status=True,
        auction_adv_target_status=True,
    )
    exec_result = MagicMock()
    exec_result.rowcount = 5
    session = AsyncMock()
    session.get = AsyncMock(return_value=adv)
    session.execute = AsyncMock(return_value=exec_result)

    result = await apply_ab_hold_emergency_in_session(session, adv_setting_id=42)

    assert result.latch_set is True
    assert result.latch_already_active is False
    assert result.status == "ok"
    assert result.keywords_blocked == 5
    assert result.target_status_paused is True
    assert adv.card_ab_hold_emergency_latch is True
    assert adv.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value
    assert adv.auto_adv_target_status is False
    assert adv.auction_adv_target_status is False
    assert SUPPORT_LINK in result.support_link


@pytest.mark.asyncio
async def test_apply_emergency_idempotent_when_latch_active() -> None:
    """Spec: Emergency is idempotent — повтор не пишет block-all заново."""
    adv = SimpleNamespace(
        id=42,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_emergency_latch=True,
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=adv)
    session.execute = AsyncMock()

    result = await apply_ab_hold_emergency_in_session(session, adv_setting_id=42)

    assert result.latch_already_active is True
    assert result.latch_set is False
    assert result.status == "already_active"
    assert result.keywords_blocked == 0
    session.execute.assert_not_awaited()
    assert adv.card_ab_hold_mode == CardAbHoldMode.PENDING_SETUP.value
    text = format_emergency_user_result_text(result)
    assert "уже активен" in text
    assert "Emergency выполнен." not in text


@pytest.mark.asyncio
async def test_apply_emergency_partial_when_block_fails() -> None:
    """Spec/design: latch+pause ASAP; block failure → честный partial, не silent ok."""
    adv = SimpleNamespace(
        id=7,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_emergency_latch=False,
        auto_adv_target_status=True,
        auction_adv_target_status=True,
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=adv)
    session.execute = AsyncMock(side_effect=RuntimeError("db boom"))

    result = await apply_ab_hold_emergency_in_session(session, adv_setting_id=7)

    assert result.status == "partial"
    assert result.latch_set is True
    assert result.target_status_paused is True
    assert result.keywords_blocked == 0
    assert result.block_error == "RuntimeError"
    assert adv.card_ab_hold_emergency_latch is True
    assert adv.card_ab_hold_mode == CardAbHoldMode.PENDING_SETUP.value
    text = format_emergency_user_result_text(result)
    assert "частично" in text.lower()
    assert "Emergency выполнен." not in text
    assert SUPPORT_LINK in text
    assert "RuntimeError" not in text
    assert "db boom" not in text


@pytest.mark.asyncio
async def test_ensure_budget_skips_when_emergency_latch() -> None:
    """Spec: ensure_budget MUST NOT top-up при ACTIVE latch (paired gate)."""
    mgr = AutoBudgetService.__new__(AutoBudgetService)
    adv = SimpleNamespace(
        adv_setting=SimpleNamespace(card_ab_hold_emergency_latch=True)
    )
    result = await mgr.ensure_budget(
        adv,  # type: ignore[arg-type]
        adv_setting_id=1,
        campaign_type=AdvType.AUTO,
        wb_manager_hub=MagicMock(),
    )
    assert result is not None
    assert result.status == AutoBudgetEnsureStatus.ADV_NOT_READY
    assert "Emergency latch" in (result.reason or "")


@pytest.mark.asyncio
async def test_ensure_common_budget_skips_when_emergency_latch() -> None:
    """Spec: ensure_common_budget MUST NOT top-up при ACTIVE latch."""
    mgr = AutoBudgetService.__new__(AutoBudgetService)
    adv = SimpleNamespace(
        adv_setting=SimpleNamespace(card_ab_hold_emergency_latch=True)
    )
    result = await mgr.ensure_common_budget(
        adv,  # type: ignore[arg-type]
        adv_setting_id=1,
        wb_manager_hub=MagicMock(),
    )
    assert result is not None
    assert result.status == AutoBudgetEnsureStatus.ADV_NOT_READY
    assert "Emergency latch" in (result.reason or "")


@pytest.mark.asyncio
async def test_ensure_budget_passes_latch_gate_when_off() -> None:
    """Paired positive: latch OFF → ordinary path достигает acquire_lock."""
    mgr = AutoBudgetService.__new__(AutoBudgetService)
    mgr._acquire_lock = AsyncMock(return_value=False)
    mgr._release_lock = AsyncMock()
    mgr._lock_key = MagicMock(return_value="k")
    adv = SimpleNamespace(
        adv_setting=SimpleNamespace(card_ab_hold_emergency_latch=False)
    )
    result = await mgr.ensure_budget(
        adv,  # type: ignore[arg-type]
        adv_setting_id=1,
        campaign_type=AdvType.AUTO,
        wb_manager_hub=MagicMock(),
    )
    assert result is not None
    assert result.status == AutoBudgetEnsureStatus.LOCK_BUSY
    mgr._acquire_lock.assert_awaited_once()


def _patch_writable_sm(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncMock:
    """Writable ``sm(read_only=False)`` session для Telegram Emergency handlers."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(emergency_handlers, "sm", MagicMock(return_value=session_cm))
    return session


@pytest.mark.asyncio
async def test_emergency_abort_does_not_mutate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Spec: Cancel confirm does nothing — apply MUST NOT вызываться."""
    apply_mock = AsyncMock()
    monkeypatch.setattr(emergency_handlers, "apply_ab_hold_emergency_in_session", apply_mock)
    notify = AsyncMock()
    monkeypatch.setattr(handlers, "_notify_callback_user", notify)
    query = MagicMock()
    cb = CardAbHoldEmergencyAbort(adv_setting_original_id=99)

    await emergency_handlers.emergency_abort(query, cb)

    apply_mock.assert_not_awaited()
    notify.assert_awaited_once()
    ack = notify.await_args.args[1]
    assert "отменён" in ack.lower()
    assert len(ack) <= _TG_CALLBACK_ANSWER_MAX


@pytest.mark.asyncio
async def test_emergency_educate_ack_happy_path_notifies_and_edits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Educate ACK ok → commit, success notify, screen с emergency_educated=True."""
    adv = SimpleNamespace(
        id=77,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        card_ab_hold_phase=None,
        card_ab_hold_emergency_latch=False,
        bot_active=True,
    )
    session = _patch_writable_sm(monkeypatch)
    monkeypatch.setattr(
        emergency_handlers,
        "acknowledge_emergency_education_in_session",
        AsyncMock(return_value=EmergencyEducateAckOutcome(kind="ok", adv=adv)),
    )
    notify = AsyncMock()
    edit = AsyncMock()
    monkeypatch.setattr(
        handlers, "_screen_status_text", AsyncMock(return_value="Статус: active")
    )
    monkeypatch.setattr(handlers, "_notify_callback_user", notify)
    monkeypatch.setattr(handlers, "_edit_screen", edit)

    query = MagicMock()
    cb = CardAbHoldEmergencyEducate(adv_setting_original_id=77)
    await emergency_handlers.emergency_educate_ack(query, cb)

    session.commit.assert_awaited()
    notify.assert_awaited_once()
    ack = notify.await_args.args[1]
    assert "Emergency доступен" in ack
    assert len(ack) <= _TG_CALLBACK_ANSWER_MAX
    edit.assert_awaited_once()
    assert edit.await_args.kwargs["emergency_educated"] is True
    assert edit.await_args.kwargs["emergency_latch"] is False
    assert edit.await_args.args[2] == 77


@pytest.mark.asyncio
async def test_emergency_educate_ack_ui_hidden_skips_commit_and_edit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ui_hidden → paid-bot deny, без commit и без edit_screen."""
    session = _patch_writable_sm(monkeypatch)
    monkeypatch.setattr(
        emergency_handlers,
        "acknowledge_emergency_education_in_session",
        AsyncMock(return_value=EmergencyEducateAckOutcome(kind="ui_hidden")),
    )
    notify = AsyncMock()
    edit = AsyncMock()
    monkeypatch.setattr(handlers, "_notify_callback_user", notify)
    monkeypatch.setattr(handlers, "_edit_screen", edit)

    query = MagicMock()
    cb = CardAbHoldEmergencyEducate(adv_setting_original_id=77)
    await emergency_handlers.emergency_educate_ack(query, cb)

    session.commit.assert_not_awaited()
    edit.assert_not_awaited()
    notify.assert_awaited_once()
    assert "включённом боте" in notify.await_args.args[1]


@pytest.mark.asyncio
async def test_emergency_educate_ack_not_visible_skips_commit_and_edit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """emergency_not_visible → mode deny, без commit и без edit_screen."""
    session = _patch_writable_sm(monkeypatch)
    monkeypatch.setattr(
        emergency_handlers,
        "acknowledge_emergency_education_in_session",
        AsyncMock(
            return_value=EmergencyEducateAckOutcome(kind="emergency_not_visible")
        ),
    )
    notify = AsyncMock()
    edit = AsyncMock()
    monkeypatch.setattr(handlers, "_notify_callback_user", notify)
    monkeypatch.setattr(handlers, "_edit_screen", edit)

    query = MagicMock()
    cb = CardAbHoldEmergencyEducate(adv_setting_original_id=77)
    await emergency_handlers.emergency_educate_ack(query, cb)

    session.commit.assert_not_awaited()
    edit.assert_not_awaited()
    notify.assert_awaited_once()
    assert "режиме A/B Hold" in notify.await_args.args[1]


@pytest.mark.asyncio
async def test_emergency_confirm_calls_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    """Spec: Confirm executes kill switch — apply вызывается, Hold mode сохранён."""
    adv = SimpleNamespace(
        id=55,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        card_ab_hold_phase=None,
        card_ab_hold_emergency_latch=False,
        bot_active=True,
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=adv)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(emergency_handlers, "sm", MagicMock(return_value=session_cm))
    monkeypatch.setattr(
        emergency_handlers,
        "is_card_ab_hold_ui_visible",
        lambda _adv: True,
    )
    apply_result = EmergencyApplyResult(
        latch_already_active=False,
        latch_set=True,
        keywords_blocked=3,
        target_status_paused=True,
        status="ok",
    )
    apply_mock = AsyncMock(return_value=apply_result)
    monkeypatch.setattr(
        emergency_handlers, "apply_ab_hold_emergency_in_session", apply_mock
    )
    notify = AsyncMock()
    edit = AsyncMock()
    monkeypatch.setattr(handlers, "_notify_callback_user", notify)
    monkeypatch.setattr(handlers, "_edit_screen", edit)

    query = MagicMock()
    cb = CardAbHoldEmergencyConfirm(adv_setting_original_id=55)
    await emergency_handlers.emergency_confirm_execute(query, cb)

    apply_mock.assert_awaited_once()
    assert apply_mock.await_args.kwargs["adv_setting_id"] == 55
    text = notify.await_args.args[1]
    assert "Emergency выполнен" in text
    assert SUPPORT_LINK in text
    assert adv.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value


@pytest.mark.asyncio
async def test_activity_force_pause_when_emergency_latch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 3.2: latch ACTIVE → force-pause Search+Auto; ordinary restart skipped."""
    adv_setting = SimpleNamespace(
        id=11,
        card_ab_hold_emergency_latch=True,
    )
    adv = SimpleNamespace(
        bot_active=True,
        auto_budget_watchdog_enabled=True,
        adv_setting=adv_setting,
        adv_id=101,
        search_adv_id=202,
    )
    wb_modifier = MagicMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()

    async def mock_run_tasks(
        handlers_list: list[Callable[[], Awaitable[None]]], *args: Any, **kwargs: Any
    ) -> list[object]:
        return [await h() for h in handlers_list]

    monkeypatch.setattr(f"{_ACTIVITY_MODULE}.run_tasks", mock_run_tasks)
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(return_value={11: None})
    monkeypatch.setattr(f"{_ACTIVITY_MODULE}._time_settings_repo", mock_ts_repo)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=MagicMock())
    session_cm.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(
        f"{_ACTIVITY_MODULE}.get_session_maker",
        MagicMock(return_value=session_cm),
    )

    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=MagicMock(),
    )
    await service.ensure_campaigns_active([adv])  # type: ignore[arg-type]

    wb_modifier.pause_auto_campaign.assert_awaited_once_with(adv)
    wb_modifier.pause_auction_campaign.assert_awaited_once_with(adv)
    wb_modifier.start_auto_campaign.assert_not_awaited()
    wb_modifier.start_auction_campaign.assert_not_awaited()


def test_emergency_callback_data_utf8_byte_limits() -> None:
    """Telegram UI: callback_data Emergency ≤ 64 UTF-8 bytes (worst-case id)."""
    callbacks = (
        CardAbHoldEmergencyEducate(adv_setting_original_id=_WORST_CASE_ADV_SETTING_ID),
        CardAbHoldEmergencyAsk(adv_setting_original_id=_WORST_CASE_ADV_SETTING_ID),
        CardAbHoldEmergencyConfirm(adv_setting_original_id=_WORST_CASE_ADV_SETTING_ID),
        CardAbHoldEmergencyAbort(adv_setting_original_id=_WORST_CASE_ADV_SETTING_ID),
    )
    for cb in callbacks:
        packed = cb.pack()
        assert 1 <= len(packed.encode("utf-8")) <= _TG_CALLBACK_DATA_BYTES_MAX, packed


def test_emergency_education_and_result_message_limits() -> None:
    """Telegram UI: education / confirm / result+support ≤ 4096; no raw placeholders."""
    edu = emergency_handlers._emergency_education_text()
    assert len(edu) <= _TG_MESSAGE_TEXT_MAX
    assert "{" not in edu and "}" not in edu
    assert SUPPORT_LINK in edu
    assert "<" not in edu and ">" not in edu

    long_campaign = "РК_<evil>&" + ("Ж" * 400)
    ok = format_emergency_user_result_text(
        EmergencyApplyResult(
            latch_already_active=False,
            latch_set=True,
            keywords_blocked=10**9,
            target_status_paused=True,
            status="ok",
        ),
        campaign_label=long_campaign,
    )
    screen = f"{ok}\n\n{handlers._INSTRUCTION}\nСтатус: {CardAbHoldMode.ACTIVE.value}"
    assert len(screen) <= _TG_MESSAGE_TEXT_MAX
    assert "{adv" not in screen.lower()
    assert SUPPORT_LINK in screen

    partial = format_emergency_user_result_text(
        EmergencyApplyResult(
            latch_already_active=False,
            latch_set=True,
            keywords_blocked=0,
            target_status_paused=True,
            status="partial",
            block_error="RuntimeError",
        ),
        campaign_label=long_campaign,
    )
    assert len(partial) <= _TG_MESSAGE_TEXT_MAX
    assert "RuntimeError" not in partial
    assert SUPPORT_LINK in partial

    confirm = emergency_handlers._emergency_confirm_prompt_text()
    assert len(confirm) <= _TG_MESSAGE_TEXT_MAX
    assert len(emergency_handlers._emergency_abort_ack_text()) <= _TG_CALLBACK_ANSWER_MAX


def test_emergency_confirm_keyboard_callback_and_support() -> None:
    """Telegram UI: confirm keyboard — callback ≤64 bytes + SUPPORT_LINK url."""
    kb = emergency_handlers.build_emergency_confirm_keyboard(_WORST_CASE_ADV_SETTING_ID)
    urls = [btn.url for row in kb.inline_keyboard for btn in row if btn.url]
    assert SUPPORT_LINK in urls
    for row in kb.inline_keyboard:
        for btn in row:
            if btn.callback_data:
                assert (
                    len(btn.callback_data.encode("utf-8")) <= _TG_CALLBACK_DATA_BYTES_MAX
                )


def test_emergency_keyboard_callback_bytes_on_screen() -> None:
    """Telegram UI: кнопки Emergency на Hold screen — callback ≤ 64 bytes."""
    kb = _screen_keyboard(
        _WORST_CASE_ADV_SETTING_ID,
        CardAbHoldMode.ACTIVE,
        emergency_educated=True,
        emergency_latch=False,
    )
    for row in kb.inline_keyboard:
        for btn in row:
            if btn.callback_data:
                assert (
                    len(btn.callback_data.encode("utf-8")) <= _TG_CALLBACK_DATA_BYTES_MAX
                )


def test_identify_emergency_telegram_payload_surfaces() -> None:
    """Inventory changed Telegram surfaces for payload-limit policy."""
    surfaces = {
        "education_text": emergency_handlers._emergency_education_text(),
        "confirm_prompt": emergency_handlers._emergency_confirm_prompt_text(),
        "abort_ack": emergency_handlers._emergency_abort_ack_text(),
        "result_ok": format_emergency_user_result_text(
            EmergencyApplyResult(
                latch_already_active=False,
                latch_set=True,
                keywords_blocked=1,
                target_status_paused=True,
                status="ok",
            )
        ),
        "result_partial": format_emergency_user_result_text(
            EmergencyApplyResult(
                latch_already_active=False,
                latch_set=True,
                keywords_blocked=0,
                target_status_paused=True,
                status="partial",
            )
        ),
        "result_already": format_emergency_user_result_text(
            EmergencyApplyResult(
                latch_already_active=True,
                latch_set=False,
                keywords_blocked=0,
                target_status_paused=False,
                status="already_active",
            )
        ),
    }
    for name, text in surfaces.items():
        assert text, name
        assert len(text) <= _TG_MESSAGE_TEXT_MAX if name != "abort_ack" else True
        if name == "abort_ack":
            assert len(text) <= _TG_CALLBACK_ANSWER_MAX
        assert "{0}" not in text
        assert "%s" not in text
