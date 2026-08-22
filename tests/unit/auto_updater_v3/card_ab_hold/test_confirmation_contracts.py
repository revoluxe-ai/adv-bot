"""Fast-local ContractCase and thin-end parity tests for A/B Hold confirmation.

Тесты сохраняют реальную candidate/validation/render/orchestration логику и
подменяют только factual/Telegram/WB transport ends. PG/CH live proof остаётся
в integration suites и не запускается без отдельной авторизации.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from app.client_bot import utils as client_bot_utils
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    confirm_handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_callbacks import (
    CahTpConfirmAll,
    ConfirmStep,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_screens import (
    build_w3_propose_text,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_handlers import (
    _notify_callback_user,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold import (
    epoch_pipelines,
)
from tests.unit.auto_updater_v3.card_ab_hold.confirmation_contract import (
    ALL_CONTRACT_CASE_IDS,
    CAH_EPOCH_FACT_DRIFT_001,
    CAH_EPOCH_PARTIAL_SYNC_001,
    CAH_EPOCH_RETRY_001,
    CAH_LIFECYCLE_CONTRACT,
    CAH_LIFECYCLE_POSITIVE_001,
    CAH_LIFECYCLE_RETRY_001,
    CAH_OWN_ASSOCIATED_001,
    CAH_OWN_FOREIGN_CONFIRM_001,
    CAH_TP_EMPTY_001,
    CAH_TP_FIELD_SEPARATION_001,
    CAH_TP_FIELD_SEPARATION_002,
    CAH_TP_MIXED_001,
    CAH_TP_MISSING_001,
    CAH_TP_NEGATIVE_001,
    CAH_TP_NONFINITE_001,
    CAH_TP_POSITIVE_001,
    CAH_TP_ZERO_001,
    FACTUAL_POSITION_CASES,
    production_factual_rows,
)


def _make_adv(*keywords: str) -> SimpleNamespace:
    """Создать production-shaped AdvSetting для чистого W3 validator path."""
    return SimpleNamespace(
        id=42,
        adv_id=4242,
        bot_active=True,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value,
        card_ab_hold_confirmed_keywords_json=list(keywords),
        card_ab_hold_confirmed_target_places_json={},
        card_ab_hold_generation=0,
        card_ab_hold_sync_status=None,
        card_ab_hold_degraded=False,
        cpm=120.0,
    )


def _make_fsm() -> FSMContext:
    """Создать изолированный FSM для Telegram render seam."""
    return FSMContext(
        storage=MemoryStorage(),
        key=StorageKey(bot_id=1, chat_id=1, user_id=1),
    )


def _make_query(*, telegram_id: int = 1) -> MagicMock:
    """Собрать production-shaped CallbackQuery с Message transport."""
    message = MagicMock(spec=Message)
    message.answer = AsyncMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.message = message
    query.from_user = SimpleNamespace(id=telegram_id)
    query.answer = AsyncMock()
    return query


def _production_keyword_loader(
    *,
    text: str,
    position: float,
) -> Callable[[object], Awaitable[list[SimpleNamespace]]]:
    """Вернуть loader с теми полями, которые читает production code."""

    async def _loader(_adv: object) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                text=text,
                cluster_stat=SimpleNamespace(position=position),
            )
        ]

    return _loader


@pytest.mark.unit
def test_confirmation_contract_registry_contains_all_packet_cases() -> None:
    """ContractCase registry сохраняет identity всех TEST_ONLY packet items."""
    required = {
        "CAH-OWN-ASSOCIATED-001",
        "CAH-OWN-FOREIGN-CONFIRM-001",
        "CAH-OWN-FOREIGN-DISABLE-001",
        "CAH-OWN-UNRELATED-WRITERS-001",
        "CAH-TP-POSITIVE-001",
        "CAH-TP-FIELD-SEPARATION-001",
        "CAH-TP-MISSING-001",
        "CAH-TP-ZERO-001",
        "CAH-TP-NEGATIVE-001",
        "CAH-TP-NONFINITE-001",
        "CAH-TP-MIXED-001",
        "CAH-TP-EMPTY-001",
        "CAH-TP-FIELD-SEPARATION-002",
        "CAH-EPOCH-RETRY-001",
        "CAH-EPOCH-PARTIAL-SYNC-001",
        "CAH-LIFECYCLE-POSITIVE-001",
        "CAH-LIFECYCLE-RETRY-001",
    }
    assert required <= ALL_CONTRACT_CASE_IDS


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [CAH_OWN_ASSOCIATED_001, CAH_OWN_FOREIGN_CONFIRM_001],
    ids=lambda case: case.case_id,
)
async def test_owner_contract_cases_drive_real_actor_gate(case: Any) -> None:
    """Ownership vectors проходять реальный ``_load_adv`` actor boundary."""
    adv = SimpleNamespace(id=42, wb_cabinet_id=7)
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=adv)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    ownership = AsyncMock(
        return_value=SimpleNamespace(id=11) if case.associated else None
    )

    with (
        patch.object(confirm_handlers, "sm", return_value=session_cm),
        patch.object(
            confirm_handlers,
            "get_wb_user_cabinet_for_adv_and_telegram",
            new=ownership,
        ),
    ):
        loaded = await confirm_handlers._load_adv(
            adv.id,
            telegram_user_id=999,
        )

    assert (loaded is not None) is case.associated
    assert case.expected_neutral_notice is (loaded is None)
    ownership.assert_awaited_once_with(session, adv, 999)


@pytest.mark.unit
@pytest.mark.parametrize("case", FACTUAL_POSITION_CASES, ids=lambda case: case.case_id)
def test_factual_contract_cases_drive_real_rows_and_render_text(case: Any) -> None:
    """Каждый factual vector проходит реальный validator и W3 formatter."""
    keywords = tuple(
        dict.fromkeys(
            [
                *case.positions,
                *(keyword for keyword, _reason in case.expected_exclusions),
                *(keyword for keyword, _fact, _target in case.expected_rows),
            ]
        )
    )
    adv = _make_adv(*keywords)
    positions = cast(dict[str, float], case.positions)

    rows, exclusions = confirm_handlers._tp_rows_and_exclusions(adv, positions)
    assert rows == list(case.expected_rows)
    assert exclusions == list(case.expected_exclusions)

    text = build_w3_propose_text(
        rows=rows,
        page=0,
        total_pages=1,
        exclusions=exclusions,
    )
    if rows:
        for keyword, fact, target in rows:
            assert f"{keyword}\n  факт: {fact}" in text
            assert f"предложенная цель: {target}" in text
    else:
        assert "Нет валидных ключей для подтверждения." in text
    for keyword, reason in exclusions:
        assert f"{keyword}: исключён — {reason}" in text


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [CAH_TP_POSITIVE_001, CAH_TP_MISSING_001, CAH_TP_EMPTY_001],
    ids=lambda case: case.case_id,
)
async def test_default_factual_loader_preserves_keyboard_request_return_empty_parity(
    case: Any,
) -> None:
    """Default keyboard boundary preserves shared row and empty-key semantics."""
    keywords = tuple(
        dict.fromkeys(
            [
                *case.positions,
                *(keyword for keyword, _reason in case.expected_exclusions),
            ]
        )
    )
    adv = _make_adv(*keywords)
    loader = AsyncMock(return_value=production_factual_rows(case))

    with patch("app.client_bot.utils.get_keywords_for_keyboard", new=loader):
        positions = await confirm_handlers._load_factual_positions(adv)

    loader.assert_awaited_once_with(adv)
    assert positions == {
        keyword: float(position) for keyword, position in case.positions.items()
    }
    assert positions.keys() == case.positions.keys()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [CAH_TP_POSITIVE_001, CAH_TP_MISSING_001],
    ids=lambda case: case.case_id,
)
async def test_get_keywords_for_keyboard_preserves_pg_request_and_return_parity(
    case: Any,
) -> None:
    """Production keyboard adapter keeps PG read mode and empty return shape."""
    adv = SimpleNamespace(
        id=42,
        adv_id=4242,
        search_adv_id=None,
        plan_for_sales_for_day=None,
        target_price_for_order=None,
        max_price_for_order=None,
    )
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one.return_value = "test-shop"
    session.execute.return_value = result
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    rows = production_factual_rows(case)
    fetch_keywords = AsyncMock(return_value=rows)
    plan_fact = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(return_value=None),
    )

    with (
        patch.object(client_bot_utils, "_sm", return_value=session_cm) as sm,
        patch.object(client_bot_utils, "PlanFactReader", return_value=plan_fact),
        patch.object(
            client_bot_utils,
            "fetch_keywords_from_database",
            new=fetch_keywords,
        ),
    ):
        returned = await client_bot_utils.get_keywords_for_keyboard(adv)

    sm.assert_called_once_with(read_only=True)
    session.execute.assert_awaited_once()
    fetch_keywords.assert_awaited_once()
    complex_adv = fetch_keywords.await_args.args[0]
    assert complex_adv.adv_setting is adv
    assert complex_adv.shop_id == "test-shop"
    assert returned == rows


@pytest.mark.unit
@pytest.mark.asyncio
async def test_injected_factual_loader_and_validator_preserve_missing_shape() -> None:
    """Injectable factual boundary preserves absence instead of inventing zero."""
    adv = _make_adv("alpha")
    loader = _production_keyword_loader(text="beta", position=14.4)

    positions = await confirm_handlers._load_factual_positions(
        adv,
        keywords_loader=loader,
    )

    rows, exclusions = confirm_handlers._tp_rows_and_exclusions(adv, positions)
    assert rows == []
    assert exclusions == [("alpha", "фактическая позиция недоступна")]
    assert 0 not in positions.values()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_telegram_render_contract_keeps_fact_and_target_provenance() -> None:
    """Telegram edit boundary receives real W3 render with separate fields."""
    adv = _make_adv("alpha")
    query = _make_query()
    state = _make_fsm()

    with patch.object(
        confirm_handlers,
        "_load_factual_positions",
        new=AsyncMock(
            return_value=CAH_TP_FIELD_SEPARATION_001.positions,
        ),
    ):
        await confirm_handlers._render_for_adv(query, adv, state)

    edit_call = query.message.edit_text.await_args
    assert edit_call is not None
    text = edit_call.args[0]
    assert "факт: 12" in text
    assert "предложенная цель: 12" in text
    assert "это два разных поля" in text
    assert query.message.answer.await_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [CAH_TP_ZERO_001, CAH_TP_NEGATIVE_001, CAH_TP_NONFINITE_001],
    ids=lambda case: case.case_id,
)
async def test_invalid_factual_boundary_vectors_reach_real_w3_guard(
    case: Any,
) -> None:
    """Raw zero/negative/non-finite rows are excluded without target zero."""
    keywords = tuple(case.positions)
    adv = _make_adv(*keywords)
    query = _make_query()
    state = _make_fsm()
    loader = AsyncMock(return_value=production_factual_rows(case))

    with patch("app.client_bot.utils.get_keywords_for_keyboard", new=loader):
        await confirm_handlers._render_for_adv(query, adv, state)

    loader.assert_awaited_once_with(adv)
    text = query.message.edit_text.await_args.args[0]
    for keyword, reason in case.expected_exclusions:
        assert f"{keyword}: исключён — {reason}" in text
    assert "0" not in text
    keyboard = query.message.edit_text.await_args.kwargs["reply_markup"]
    assert all(
        "Подтвердить целевые позиции" not in button.text
        for row in keyboard.inline_keyboard
        for button in row
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_field_separation_002_uses_independent_factual_loader_provenance() -> None:
    """CAH-TP-FIELD-SEPARATION-002 reaches rows through the default loader."""
    case = CAH_TP_FIELD_SEPARATION_002
    adv = _make_adv("alpha")
    query = _make_query()
    state = _make_fsm()
    loader = AsyncMock(return_value=production_factual_rows(case))

    with patch("app.client_bot.utils.get_keywords_for_keyboard", new=loader):
        await confirm_handlers._render_for_adv(query, adv, state)

    loader.assert_awaited_once_with(adv)
    text = query.message.edit_text.await_args.args[0]
    assert "alpha\n  факт: 12" in text
    assert "предложенная цель: 12" in text
    rows, exclusions = confirm_handlers._tp_rows_and_exclusions(
        adv, case.positions
    )
    assert rows == list(case.expected_rows)
    assert exclusions == list(case.expected_exclusions)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_neutral_telegram_notification_uses_message_answer_only() -> None:
    """Neutral foreign notice matches Telegram boundary and ACK policy."""
    query = _make_query(telegram_id=999)
    notice = "Доступно только при включённом боте"

    await _notify_callback_user(query, notice)

    query.message.answer.assert_awaited_once_with(notice)
    query.answer.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confirmation_callback_selects_only_target_place_writer() -> None:
    """Callback writer-selection seam excludes unrelated confirmation writers."""
    case = CAH_TP_MIXED_001
    adv = _make_adv("alpha", "beta")
    query = _make_query()
    state = _make_fsm()
    callback_data = CahTpConfirmAll(
        adv_setting_original_id=adv.id,
        step=ConfirmStep.W3_PROPOSE.value,
        revision=1,
        page=0,
    )
    target_writer = AsyncMock()
    keyword_writer = AsyncMock()
    auto_participation_writer = AsyncMock()
    auto_bid_writer = AsyncMock()

    with (
        patch.object(
            confirm_handlers,
            "_load_adv",
            new=AsyncMock(side_effect=[adv, adv]),
        ),
        patch.object(
            confirm_handlers,
            "_load_factual_positions",
            new=AsyncMock(return_value=case.positions),
        ),
        patch.object(confirm_handlers, "confirm_target_places", new=target_writer),
        patch.object(
            confirm_handlers,
            "confirm_keyword_set_and_start_warmup",
            new=keyword_writer,
        ),
        patch.object(
            confirm_handlers,
            "confirm_auto_participation",
            new=auto_participation_writer,
        ),
        patch.object(confirm_handlers, "confirm_auto_bid", new=auto_bid_writer),
        patch.object(confirm_handlers, "is_card_ab_hold_ui_visible", return_value=True),
        patch.object(
            confirm_handlers,
            "_check_stale",
            new=AsyncMock(return_value=False),
        ),
    ):
        await confirm_handlers.on_tp_confirm_all(query, callback_data, state)

    target_writer.assert_awaited_once_with(
        adv.id,
        {keyword: target for keyword, _fact, target in case.expected_rows},
    )
    keyword_writer.assert_not_awaited()
    auto_participation_writer.assert_not_awaited()
    auto_bid_writer.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wb_sync_success_contract_matches_allowed_set_request() -> None:
    """WB stub receives normalized allowed-set request and response shape."""
    case = CAH_EPOCH_RETRY_001
    enforce = AsyncMock(return_value=case.enforce_response)
    manager = SimpleNamespace(enforce_frozen_allowed_set=enforce)
    complex_adv = SimpleNamespace(
        adv_id=9305,
        nmids=[],
        auto_adv_id=None,
        adv_setting=SimpleNamespace(id=305, card_ab_hold_degraded=False),
    )
    wb_hub = object()

    with patch.object(
        epoch_pipelines,
        "MinusPhraseManagerContainer",
        return_value=SimpleNamespace(minus_phrase_manager=lambda: manager),
    ) as container:
        await epoch_pipelines.sync_intent_to_wb(
            complex_adv,
            intent={
                "keywords": list(case.keywords),
                "auto_participation": False,
                "auto_bid": 0,
            },
            wb_manager_hub=wb_hub,
        )

    container.assert_called_once_with(_wb_api_manager_hub=wb_hub)
    enforce.assert_awaited_once_with(
        complex_adv,
        list(case.expected_allowed_snapshot),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wb_sync_failure_contract_preserves_exception_for_retry() -> None:
    """WB failure shape bubbles to epoch retry handler unchanged."""
    case = CAH_EPOCH_PARTIAL_SYNC_001
    enforce = AsyncMock(side_effect=RuntimeError(case.failure_message))
    manager = SimpleNamespace(enforce_frozen_allowed_set=enforce)
    complex_adv = SimpleNamespace(
        adv_id=9306,
        nmids=[],
        auto_adv_id=None,
        adv_setting=SimpleNamespace(id=306, card_ab_hold_degraded=False),
    )

    with patch.object(
        epoch_pipelines,
        "MinusPhraseManagerContainer",
        return_value=SimpleNamespace(minus_phrase_manager=lambda: manager),
    ):
        with pytest.raises(RuntimeError, match=case.failure_message):
            await epoch_pipelines.sync_intent_to_wb(
                complex_adv,
                intent={
                    "keywords": list(case.keywords),
                    "auto_participation": False,
                    "auto_bid": 0,
                },
                wb_manager_hub=object(),
            )

    enforce.assert_awaited_once()


@pytest.mark.unit
def test_missing_and_invalid_contract_vectors_never_create_zero_rows() -> None:
    """Missing/zero/negative/non-finite cases have no candidate target zero."""
    for case in (
        CAH_TP_MISSING_001,
        CAH_TP_ZERO_001,
        CAH_TP_NEGATIVE_001,
        CAH_TP_NONFINITE_001,
        CAH_TP_EMPTY_001,
    ):
        assert all(target > 0 for _keyword, _fact, target in case.expected_rows)
        assert case.expected_rows == ()


@pytest.mark.unit
def test_epoch_and_lifecycle_contract_identities_remain_bound() -> None:
    """Retry/drift/lifecycle identities не теряются при test-only wiring."""
    assert CAH_EPOCH_FACT_DRIFT_001.case_id in ALL_CONTRACT_CASE_IDS
    assert CAH_EPOCH_RETRY_001.case_id in ALL_CONTRACT_CASE_IDS
    assert CAH_EPOCH_PARTIAL_SYNC_001.case_id in ALL_CONTRACT_CASE_IDS
    assert CAH_LIFECYCLE_POSITIVE_001 in ALL_CONTRACT_CASE_IDS
    assert CAH_LIFECYCLE_RETRY_001 in ALL_CONTRACT_CASE_IDS
    assert CAH_LIFECYCLE_CONTRACT.redis_enter_events == ("enter",)
