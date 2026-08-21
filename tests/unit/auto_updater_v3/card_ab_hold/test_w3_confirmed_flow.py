"""Unit-тесты W3-confirmed UX между TP confirm и A1 (ux contract §7).

Также regression: W3 fact/proposed TP берутся из live read-model позиций,
а не из фантомного ``card_ab_hold_factual_positions_json`` на AdvSetting
(decision ``ab-hold-confirmed-epoch-parameters-sot`` §2).

На d999e49 suite пропустил баг, потому что fixture сам сажал фантомное
поле на SimpleNamespace — тесты зеленели без колонки, migration и write-path.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from sqlalchemy import inspect as sa_inspect

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write import (
    EpochWriteError,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    confirm_handlers,
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_keyboards import (
    build_w3_propose_keyboard,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_callbacks import (
    CahConfirmBack,
    CahTpConfirmAll,
    ConfirmStep,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_screens import (
    build_w3_propose_text,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_draft import (
    is_w3_confirmed_visible,
    load_draft,
    should_show_w3_confirmed_read_only,
)
from tests.unit.auto_updater_v3.card_ab_hold.confirmation_contract import (
    CAH_EPOCH_FACT_DRIFT_001,
    CAH_TP_FIELD_SEPARATION_002,
    production_factual_rows,
)


def _make_fsm() -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=1, user_id=1)
    return FSMContext(storage=storage, key=key)


def _make_adv(*, phase: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=42,
        adv_id=4242,
        bot_active=True,
        automatic_version=3,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_phase=phase,
        card_ab_hold_confirmed_keywords_json=["alpha", "beta"],
        card_ab_hold_confirmed_target_places_json={"alpha": 5, "beta": 8},
        card_ab_hold_generation=0,
        card_ab_hold_sync_status=None,
        card_ab_hold_degraded=False,
        cpm=120.0,
    )


def _adv_after_tp_confirm(adv: SimpleNamespace) -> SimpleNamespace:
    """Adv после durable confirm_target_places (phase → A1 gate)."""
    return SimpleNamespace(
        **{
            **adv.__dict__,
            "card_ab_hold_phase": (
                CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM.value
            ),
        }
    )


def _make_query() -> MagicMock:
    msg = MagicMock(spec=Message)
    msg.edit_text = AsyncMock()
    msg.answer = AsyncMock()
    query = MagicMock()
    query.message = msg
    query.answer = AsyncMock()
    query.from_user = SimpleNamespace(id=1)
    return query


_LIVE_POSITIONS = {"alpha": 14.4, "beta": 9.2}

_EPOCH_MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "alembic_"
    / "versions"
    / "d0e1f2a3b4c5_add_card_ab_hold_epoch_lifecycle_fields.py"
)


@pytest.mark.unit
def test_advsetting_has_no_factual_positions_column_or_migration() -> None:
    """Reality gate: фантомного ``card_ab_hold_factual_positions_json`` нет в ORM/migration.

    Без этого fixture может посадить attr на stub и скрыть missing write-path.
    """
    cols = sa_inspect(AdvSetting).columns
    assert "card_ab_hold_factual_positions_json" not in cols
    assert not hasattr(AdvSetting, "card_ab_hold_factual_positions_json")
    migration = _EPOCH_MIGRATION.read_text(encoding="utf-8")
    assert "card_ab_hold_factual_positions_json" not in migration


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_factual_positions_uses_keyboard_read_model() -> None:
    """``_load_factual_positions`` читает live keyboard path, не AdvSetting attr."""
    adv = SimpleNamespace(
        id=42,
        card_ab_hold_factual_positions_json={"alpha": 99.0},
    )
    kw_alpha = SimpleNamespace(
        text="alpha", cluster_stat=SimpleNamespace(position=14.4)
    )
    kw_beta = SimpleNamespace(
        text="beta", cluster_stat=SimpleNamespace(position=9.2)
    )
    with patch(
        "app.client_bot.utils.get_keywords_for_keyboard",
        new=AsyncMock(return_value=[kw_alpha, kw_beta]),
    ) as mock_fetch:
        positions = await confirm_handlers._load_factual_positions(adv)

    mock_fetch.assert_awaited_once_with(adv)
    assert positions == {"alpha": 14.4, "beta": 9.2}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_factual_positions_uses_injected_keywords_loader() -> None:
    """Injectable ``keywords_loader`` bypasses default keyboard/CH path."""
    adv = SimpleNamespace(id=7)
    kw = SimpleNamespace(text="gamma", cluster_stat=SimpleNamespace(position=3.5))
    loader = AsyncMock(return_value=[kw])

    with patch(
        "app.client_bot.utils.get_keywords_for_keyboard",
        new=AsyncMock(side_effect=AssertionError("default loader must not run")),
    ):
        positions = await confirm_handlers._load_factual_positions(
            adv, keywords_loader=loader
        )

    loader.assert_awaited_once_with(adv)
    assert positions == {"gamma": 3.5}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_adv_rejects_foreign_callback_actor() -> None:
    """Foreign callback actor не получает AdvSetting для confirm-flow.

    Regression для spec ``card-ab-hold-mode``: один callback ID не является
    доказательством ownership; actor должен быть связан с кабинетом кампании.
    """
    adv = SimpleNamespace(id=42, wb_cabinet_id=7)
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=adv)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    ownership = AsyncMock(return_value=None)

    with (
        patch.object(confirm_handlers, "sm", return_value=session_cm),
        patch.object(
            confirm_handlers,
            "get_wb_user_cabinet_for_adv_and_telegram",
            new=ownership,
        ),
    ):
        loaded = await confirm_handlers._load_adv(
            42,
            telegram_user_id=999,
        )

    assert loaded is None
    ownership.assert_awaited_once_with(session, adv, 999)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_adv_allows_related_callback_actor() -> None:
    """Related callback actor проходит ownership gate без изменения ID schema."""
    adv = SimpleNamespace(id=42, wb_cabinet_id=7)
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=adv)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    ownership = AsyncMock(return_value=SimpleNamespace(id=11))

    with (
        patch.object(confirm_handlers, "sm", return_value=session_cm),
        patch.object(
            confirm_handlers,
            "get_wb_user_cabinet_for_adv_and_telegram",
            new=ownership,
        ),
    ):
        loaded = await confirm_handlers._load_adv(
            42,
            telegram_user_id=100,
        )

    assert loaded is adv
    ownership.assert_awaited_once_with(session, adv, 100)


@pytest.mark.unit
def test_tp_rows_use_passed_live_positions_not_adv_attr() -> None:
    """Fact/proposed берутся из positions-аргумента; фантомный attr на adv игнорируется."""
    case = CAH_TP_FIELD_SEPARATION_002
    adv = SimpleNamespace(
        card_ab_hold_confirmed_keywords_json=["alpha"],
        card_ab_hold_confirmed_target_places_json={},
        card_ab_hold_factual_positions_json={"alpha": 99.0},
    )
    rows = confirm_handlers._tp_rows_from_adv(adv, case.positions)
    assert rows == list(case.expected_rows)
    assert rows[0][1] != adv.card_ab_hold_factual_positions_json["alpha"]


@pytest.mark.unit
def test_tp_rows_empty_positions_do_not_invent_facts() -> None:
    """Без live positions ключ исключается, а нулевой target не создаётся.

    Regression для spec ``card-ab-hold-mode``: отсутствие live-факта не должно
    превращаться в участника эксперимента с сохранённым ``target_place=0``.
    """
    adv = SimpleNamespace(
        card_ab_hold_confirmed_keywords_json=["alpha"],
        card_ab_hold_confirmed_target_places_json={},
        card_ab_hold_factual_positions_json={"alpha": 7.0},
    )
    rows = confirm_handlers._tp_rows_from_adv(adv, {})
    assert rows == []


@pytest.mark.unit
@pytest.mark.parametrize(
    ("position", "expected_rows"),
    [
        (0.0, []),
        (-1.0, []),
        (float("nan"), []),
        (float("inf"), []),
        (12.0, [("alpha", 12, 12)]),
    ],
)
def test_tp_rows_keep_only_finite_positive_positions(
    position: float,
    expected_rows: list[tuple[str, int, int]],
) -> None:
    """W3 подтверждает только finite positive factual positions.

    Regression для spec ``card-ab-hold-mode``: zero, negative и non-finite
    значения не должны доходить до candidate ``tp_map``.
    """
    adv = SimpleNamespace(
        card_ab_hold_confirmed_keywords_json=["alpha"],
        card_ab_hold_confirmed_target_places_json={},
    )

    assert confirm_handlers._tp_rows_from_adv(adv, {"alpha": position}) == expected_rows


@pytest.mark.unit
def test_tp_rows_keep_valid_subset_when_other_positions_are_invalid() -> None:
    """Mixed W3-набор сохраняет только валидные ключи.

    Regression для spec ``card-ab-hold-mode``: один отсутствующий или
    неположительный факт не должен блокировать и не должен загрязнять
    подтверждение остальных положительных ключей.
    """
    adv = SimpleNamespace(
        card_ab_hold_confirmed_keywords_json=["alpha", "beta", "gamma"],
        card_ab_hold_confirmed_target_places_json={},
    )

    rows = confirm_handlers._tp_rows_from_adv(
        adv,
        {"alpha": 14.0, "beta": 0.0},
    )

    assert rows == [("alpha", 14, 14)]


@pytest.mark.unit
def test_w3_exclusions_are_visible_and_empty_set_has_no_confirm_button() -> None:
    """W3 сообщает причины исключений и блокирует пустое подтверждение."""
    text = build_w3_propose_text(
        rows=[("alpha", 14, 14)],
        page=0,
        total_pages=1,
        exclusions=[
            ("beta", "фактическая позиция недоступна"),
            ("gamma", "фактическая позиция неположительная"),
        ],
    )
    assert "beta: исключён — фактическая позиция недоступна" in text
    assert "gamma: исключён — фактическая позиция неположительная" in text

    keyboard = build_w3_propose_keyboard(
        adv_id=42,
        rows=[],
        revision=1,
        page=0,
    )
    button_texts = [
        button.text
        for row in keyboard.inline_keyboard
        for button in row
    ]
    assert "Подтвердить целевые позиции" not in button_texts


@pytest.mark.unit
@pytest.mark.asyncio
async def test_w3_render_shows_exclusion_reasons_from_live_positions() -> None:
    """W3 render path показывает конкретную причину исключения ключа."""
    state = _make_fsm()
    adv = _make_adv(phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value)
    query = _make_query()

    with patch.object(
        confirm_handlers,
        "_load_factual_positions",
        new=AsyncMock(return_value={"alpha": 14.0, "beta": 0.0}),
    ):
        await confirm_handlers._render_for_adv(query, adv, state)

    text = query.message.edit_text.await_args.args[0]
    assert "beta: исключён — фактическая позиция неположительная" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_w3_render_keeps_positive_fact_and_proposed_target_separate() -> None:
    """S04/S07: positive live fact remains confirmable and separately labeled."""
    case = CAH_TP_FIELD_SEPARATION_002
    state = _make_fsm()
    adv = _make_adv(phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value)
    adv.card_ab_hold_confirmed_keywords_json = ["alpha"]
    adv.card_ab_hold_confirmed_target_places_json = {}
    query = _make_query()

    with patch.object(
        confirm_handlers,
        "_load_factual_positions",
        new=AsyncMock(return_value=case.positions),
    ):
        await confirm_handlers._render_for_adv(query, adv, state)

    edit_args = query.message.edit_text.await_args
    text = edit_args.args[0]
    keyboard = edit_args.kwargs["reply_markup"]
    assert "факт: 12" in text
    assert "предложенная цель: 12" in text
    button_texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "Подтвердить целевые позиции" in button_texts


@pytest.mark.unit
@pytest.mark.asyncio
async def test_direct_disable_rejects_foreign_actor_before_commit() -> None:
    """Прямой EXIT не меняет PG при отсутствии cabinet ownership."""
    adv = SimpleNamespace(
        id=42,
        bot_active=True,
        wb_cabinet_id=7,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        card_ab_hold_allowed_phrases_snapshot={"allowed": ["alpha"]},
    )
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=adv)
    ownership = AsyncMock(return_value=None)

    with patch.object(
        handlers,
        "get_wb_user_cabinet_for_adv_and_telegram",
        new=ownership,
    ):
        result = await handlers.disable_card_ab_hold_in_session(
            session,
            42,
            telegram_user_id=999,
        )

    assert result is None
    assert adv.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value
    session.commit.assert_not_awaited()
    ownership.assert_awaited_once_with(session, adv, 999)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_direct_disable_rejects_missing_cabinet_id_before_commit() -> None:
    """Прямой EXIT fail-closed при actor задан, но ``wb_cabinet_id`` отсутствует."""
    adv = SimpleNamespace(
        id=42,
        bot_active=True,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        card_ab_hold_allowed_phrases_snapshot={"allowed": ["alpha"]},
    )
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=adv)
    ownership = AsyncMock(return_value=SimpleNamespace(id=11))

    with patch.object(
        handlers,
        "get_wb_user_cabinet_for_adv_and_telegram",
        new=ownership,
    ):
        result = await handlers.disable_card_ab_hold_in_session(
            session,
            42,
            telegram_user_id=999,
        )

    assert result is None
    assert adv.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value
    session.commit.assert_not_awaited()
    ownership.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tp_confirm_all_persists_proposed_from_live_positions() -> None:
    """tp_confirm_all пишет proposed TP из live positions, не нули."""
    state = _make_fsm()
    adv = _make_adv(phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value)
    adv.card_ab_hold_confirmed_target_places_json = {}
    adv_after = _adv_after_tp_confirm(adv)
    query = _make_query()
    callback_data = CahTpConfirmAll(
        adv_setting_original_id=adv.id,
        step=ConfirmStep.W3_PROPOSE.value,
        revision=1,
        page=0,
    )
    confirm_mock = AsyncMock()

    with (
        patch.object(
            confirm_handlers,
            "_load_adv",
            new=AsyncMock(side_effect=[adv, adv_after]),
        ),
        patch.object(
            confirm_handlers,
            "_load_factual_positions",
            new=AsyncMock(return_value=_LIVE_POSITIONS),
        ),
        patch.object(
            confirm_handlers,
            "confirm_target_places",
            new=confirm_mock,
        ),
        patch.object(
            confirm_handlers,
            "is_card_ab_hold_ui_visible",
            return_value=True,
        ),
        patch.object(
            confirm_handlers,
            "_check_stale",
            new=AsyncMock(return_value=False),
        ),
    ):
        await confirm_handlers.on_tp_confirm_all(query, callback_data, state)

    confirm_mock.assert_awaited_once_with(42, {"alpha": 14, "beta": 9})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tp_confirm_all_drops_invalid_mixed_positions_before_writer() -> None:
    """Полный authoritative read передаёт writer только positive subset.

    Все durable ключи присутствуют в ответе; beta и gamma явно имеют
    неположительные/невалидные факты и поэтому могут быть исключены.
    """
    state = _make_fsm()
    adv = _make_adv(phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value)
    adv.card_ab_hold_confirmed_keywords_json = ["alpha", "beta", "gamma"]
    adv.card_ab_hold_confirmed_target_places_json = {}
    query = _make_query()
    callback_data = CahTpConfirmAll(
        adv_setting_original_id=adv.id,
        step=ConfirmStep.W3_PROPOSE.value,
        revision=1,
        page=0,
    )
    confirm_mock = AsyncMock()

    with (
        patch.object(
            confirm_handlers,
            "_load_adv",
            new=AsyncMock(side_effect=[adv, _adv_after_tp_confirm(adv)]),
        ),
        patch.object(
            confirm_handlers,
            "_load_factual_positions",
            new=AsyncMock(
                return_value={"alpha": 14.0, "beta": 0.0, "gamma": float("nan")}
            ),
        ),
        patch.object(
            confirm_handlers,
            "confirm_target_places",
            new=confirm_mock,
        ),
        patch.object(
            confirm_handlers,
            "is_card_ab_hold_ui_visible",
            return_value=True,
        ),
        patch.object(
            confirm_handlers,
            "_check_stale",
            new=AsyncMock(return_value=False),
        ),
    ):
        await confirm_handlers.on_tp_confirm_all(query, callback_data, state)

    confirm_mock.assert_awaited_once_with(42, {"alpha": 14})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tp_confirm_all_does_not_shrink_durable_set_for_partial_live_read() -> None:
    """Частичный live-read не должен трактоваться как полный durable-result.

    В отличие от соседнего сценария, где ``beta`` присутствует в полном
    authoritative read с неположительным фактом, отсутствие ``beta`` здесь
    означает неполный ответ источника. Такой ответ не может удалить ``beta``
    из durable confirmed set.
    """
    state = _make_fsm()
    adv = _make_adv(phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value)
    query = _make_query()
    callback_data = CahTpConfirmAll(
        adv_setting_original_id=adv.id,
        step=ConfirmStep.W3_PROPOSE.value,
        revision=1,
        page=0,
    )
    partial_positions = {"alpha": 14.0}
    assert set(partial_positions) < set(adv.card_ab_hold_confirmed_keywords_json)

    async def apply_confirmed_payload(
        _adv_setting_id: int,
        tp_map: dict[str, int],
    ) -> None:
        """Смоделировать durable write после callback boundary."""
        current_keywords = list(adv.card_ab_hold_confirmed_keywords_json)
        adv.card_ab_hold_confirmed_keywords_json = [
            keyword for keyword in current_keywords if keyword in tp_map
        ]
        adv.card_ab_hold_confirmed_target_places_json = dict(tp_map)

    confirm_mock = AsyncMock(side_effect=apply_confirmed_payload)

    with (
        patch.object(
            confirm_handlers,
            "_load_adv",
            new=AsyncMock(side_effect=[adv, _adv_after_tp_confirm(adv)]),
        ),
        patch.object(
            confirm_handlers,
            "_load_factual_positions",
            new=AsyncMock(return_value=partial_positions),
        ),
        patch.object(
            confirm_handlers,
            "confirm_target_places",
            new=confirm_mock,
        ),
        patch.object(
            confirm_handlers,
            "is_card_ab_hold_ui_visible",
            return_value=True,
        ),
        patch.object(
            confirm_handlers,
            "_check_stale",
            new=AsyncMock(return_value=False),
        ),
    ):
        await confirm_handlers.on_tp_confirm_all(query, callback_data, state)

    confirm_mock.assert_not_awaited()
    assert adv.card_ab_hold_confirmed_keywords_json == ["alpha", "beta"]
    assert adv.card_ab_hold_confirmed_target_places_json == {"alpha": 5, "beta": 8}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tp_confirm_all_stops_when_no_valid_positions_remain() -> None:
    """Полностью invalid W3-набор не вызывает writer и phase transition."""
    state = _make_fsm()
    adv = _make_adv(phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value)
    adv.card_ab_hold_confirmed_keywords_json = ["alpha"]
    adv.card_ab_hold_confirmed_target_places_json = {}
    query = _make_query()
    callback_data = CahTpConfirmAll(
        adv_setting_original_id=adv.id,
        step=ConfirmStep.W3_PROPOSE.value,
        revision=1,
        page=0,
    )
    confirm_mock = AsyncMock()

    with (
        patch.object(
            confirm_handlers,
            "_load_adv",
            new=AsyncMock(return_value=adv),
        ),
        patch.object(
            confirm_handlers,
            "_load_factual_positions",
            new=AsyncMock(return_value={"alpha": float("nan")}),
        ),
        patch.object(
            confirm_handlers,
            "confirm_target_places",
            new=confirm_mock,
        ),
        patch.object(
            confirm_handlers,
            "is_card_ab_hold_ui_visible",
            return_value=True,
        ),
        patch.object(
            confirm_handlers,
            "_check_stale",
            new=AsyncMock(return_value=False),
        ),
    ):
        await confirm_handlers.on_tp_confirm_all(query, callback_data, state)

    confirm_mock.assert_not_awaited()
    assert "Нет валидных ключей" in query.message.answer.await_args.args[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tp_confirm_all_recovers_from_concurrent_epoch_write_error() -> None:
    """Race на durable TP write не должен ронять callback без recovery."""
    state = _make_fsm()
    adv = _make_adv(phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value)
    adv.card_ab_hold_confirmed_target_places_json = {}
    query = _make_query()
    callback_data = CahTpConfirmAll(
        adv_setting_original_id=adv.id,
        step=ConfirmStep.W3_PROPOSE.value,
        revision=1,
        page=0,
    )
    notify_mock = AsyncMock()
    render_mock = AsyncMock()
    write_mock = AsyncMock(
        side_effect=EpochWriteError(
            "confirm_target_places requires AWAITING_TP_CONFIRM, got WARM_UP"
        )
    )
    set_visible_mock = AsyncMock()
    bump_mock = AsyncMock()

    with (
        patch.object(
            confirm_handlers,
            "_load_adv",
            new=AsyncMock(return_value=adv),
        ),
        patch.object(
            confirm_handlers,
            "_load_factual_positions",
            new=AsyncMock(return_value=_LIVE_POSITIONS),
        ),
        patch.object(confirm_handlers, "confirm_target_places", new=write_mock),
        patch.object(confirm_handlers, "_notify_callback_user", new=notify_mock),
        patch.object(confirm_handlers, "_render_for_adv", new=render_mock),
        patch.object(
            confirm_handlers,
            "set_w3_confirmed_visible",
            new=set_visible_mock,
        ),
        patch.object(confirm_handlers, "bump_revision", new=bump_mock),
        patch.object(
            confirm_handlers,
            "is_card_ab_hold_ui_visible",
            return_value=True,
        ),
        patch.object(
            confirm_handlers,
            "_check_stale",
            new=AsyncMock(return_value=False),
        ),
    ):
        await confirm_handlers.on_tp_confirm_all(query, callback_data, state)

    write_mock.assert_awaited_once_with(42, {"alpha": 14, "beta": 9})
    notify_mock.assert_awaited_once()
    render_mock.assert_awaited_once_with(query, adv, state)
    set_visible_mock.assert_not_awaited()
    bump_mock.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tp_confirm_all_sets_w3_confirmed_and_renders_read_only() -> None:
    """После tp_confirm_all показывается W3-confirmed, не A1."""
    state = _make_fsm()
    adv = _make_adv(phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value)
    adv_after = _adv_after_tp_confirm(adv)
    query = _make_query()
    callback_data = CahTpConfirmAll(
        adv_setting_original_id=adv.id,
        step=ConfirmStep.W3_PROPOSE.value,
        revision=1,
        page=0,
    )

    with (
        patch.object(
            confirm_handlers,
            "_load_adv",
            new=AsyncMock(side_effect=[adv, adv_after]),
        ),
        patch.object(
            confirm_handlers,
            "_load_factual_positions",
            new=AsyncMock(return_value=_LIVE_POSITIONS),
        ),
        patch.object(
            confirm_handlers,
            "confirm_target_places",
            new=AsyncMock(),
        ),
        patch.object(
            confirm_handlers,
            "is_card_ab_hold_ui_visible",
            return_value=True,
        ),
        patch.object(
            confirm_handlers,
            "_check_stale",
            new=AsyncMock(return_value=False),
        ),
    ):
        await confirm_handlers.on_tp_confirm_all(query, callback_data, state)

    draft = await load_draft(state, adv.id)
    assert is_w3_confirmed_visible(draft) is True
    edit_args = query.message.edit_text.await_args
    assert edit_args is not None
    text = edit_args.args[0] if edit_args.args else edit_args.kwargs.get("text", "")
    assert "зафиксированы для текущей эпохи" in text
    assert "Участие Auto" not in text
    kb = edit_args.kwargs.get("reply_markup")
    button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "Продолжить →" in button_texts


@pytest.mark.unit
@pytest.mark.asyncio
async def test_back_from_a1_lands_on_w3_confirmed_not_propose() -> None:
    """Back с A1 → W3-confirmed (read-only), не editable W3-propose и не summary."""
    state = _make_fsm()
    adv = _make_adv(
        phase=CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM.value
    )
    query = _make_query()
    callback_data = CahConfirmBack(
        adv_setting_original_id=adv.id,
        step=ConfirmStep.A1.value,
        revision=1,
        page=0,
    )

    with (
        patch.object(
            confirm_handlers,
            "_load_adv",
            new=AsyncMock(side_effect=[adv, adv]),
        ),
        patch.object(
            confirm_handlers,
            "_load_factual_positions",
            new=AsyncMock(return_value=_LIVE_POSITIONS),
        ),
        patch.object(
            confirm_handlers,
            "is_card_ab_hold_ui_visible",
            return_value=True,
        ),
        patch.object(
            confirm_handlers,
            "_check_stale",
            new=AsyncMock(return_value=False),
        ),
    ):
        await confirm_handlers.on_back(query, callback_data, state)

    draft = await load_draft(state, adv.id)
    assert is_w3_confirmed_visible(draft) is True
    assert draft.get("summary_visible") is not True
    edit_args = query.message.edit_text.await_args
    text = edit_args.args[0] if edit_args.args else edit_args.kwargs.get("text", "")
    assert "зафиксированы для текущей эпохи" in text
    assert "предложенная цель" not in text
    assert "Участие Auto" not in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_after_restart_shows_w3_confirmed_from_durable_tp() -> None:
    """Restart recovery: пустой FSM + durable TP + A1 phase → W3-confirmed (§7)."""
    state = _make_fsm()
    adv = _make_adv(
        phase=CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM.value
    )
    query = _make_query()
    draft = await load_draft(state, adv.id)
    assert is_w3_confirmed_visible(draft) is False
    assert should_show_w3_confirmed_read_only(adv, draft) is True

    with (
        patch.object(
            confirm_handlers,
            "is_card_ab_hold_ui_visible",
            return_value=True,
        ),
        patch.object(
            confirm_handlers,
            "_load_factual_positions",
            new=AsyncMock(return_value=_LIVE_POSITIONS),
        ),
    ):
        await confirm_handlers._render_for_adv(query, adv, state)

    edit_args = query.message.edit_text.await_args
    assert edit_args is not None
    text = edit_args.args[0] if edit_args.args else edit_args.kwargs.get("text", "")
    assert "зафиксированы для текущей эпохи" in text
    assert "Участие Auto" not in text
    kb = edit_args.kwargs.get("reply_markup")
    button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "Продолжить →" in button_texts


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fact_position_drift_keeps_confirmed_target_immutable() -> None:
    """S11: drifted live fact is rendered without reopening or recalculating TP.

    Regression для spec ``card-ab-hold-mode``: a later factual-position read
    changes only the live fact field while the durable confirmed target remains
    the epoch source of truth.
    """
    case = CAH_EPOCH_FACT_DRIFT_001
    state = _make_fsm()
    adv = _make_adv(
        phase=CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM.value
    )
    adv.card_ab_hold_confirmed_keywords_json = ["alpha"]
    adv.card_ab_hold_confirmed_target_places_json = {"alpha": 7}
    query = _make_query()

    factual_rows = production_factual_rows(
        CAH_TP_FIELD_SEPARATION_002
    )
    factual_rows[0].cluster_stat.position = case.factual_position
    with patch(
        "app.client_bot.utils.get_keywords_for_keyboard",
        new=AsyncMock(return_value=factual_rows),
    ) as factual_loader:
        await confirm_handlers._render_for_adv(query, adv, state)

    factual_loader.assert_awaited_once_with(adv)
    text = query.message.edit_text.await_args.args[0]
    assert "факт: 18" in text
    assert "цель: 7 (зафиксирована)" in text
    assert "Подтвердить целевые позиции" not in text
