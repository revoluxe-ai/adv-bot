"""PENDING_SETUP liveness: max-CPO enable gate + actionable status + EXIT recovery.

Spec ``card-ab-hold-mode`` — Requirements «Enable is blocked when plan max CPO is
missing or non-positive» и «PENDING_SETUP setup blockers are surfaced and
recoverable». Decision ``card-ab-hold-write-path-ownership`` §14:

- §14a: enable hard-gate ``max_price_for_order > 0`` (mode остаётся OFF + причина),
  до §2c soft-gate;
- §14b: детерминированный блок setup (пустой allowed-set / пропавший max CPO) →
  actionable-причина в статусе PENDING (не generic «Подготовка…»);
- §14c: MVP recovery = actionable reason + всегда доступный EXIT (owned авто-abort
  вынесен в future, без ``pending_since`` миграции).

Класс: unit. Handler / pipeline с замоканными session / Redis / lock / apply.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.enter_status import (
    build_enter_poll_status_lines,
    setup_block_reason_line,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.launch_validity_gate import (
    LaunchViewVolumeEvaluation,
    LaunchViewVolumeOutcome,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldSetupBlockKind,
    is_ab_hold_structural_freeze,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.pipelines import (
    process_ab_setup,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldDisable,
    CardAbHoldEnable,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.ui_access import (
    card_ab_hold_requires_max_cpo_message,
    has_positive_plan_max_cpo,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)

_PIPELINES = (
    "app.modules.shop_runner.service_manager.services."
    "auto_updater_v3.card_ab_hold.pipelines"
)
_TG_MESSAGE_TEXT_MAX = 4096


# --- 16.1/16.2: max-CPO ENTER hard-gate (decision §14a) ---


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw_max_cpo", "expected"),
    [
        (100, True),
        (0.5, True),
        (1, True),
        (0, False),
        (-5, False),
        (None, False),
        ("abc", False),
    ],
)
def test_has_positive_plan_max_cpo_boundary(
    raw_max_cpo: object, expected: bool
) -> None:
    """16.1: предикат True только для строго положительного плана max CPO."""
    adv = SimpleNamespace(max_price_for_order=raw_max_cpo)
    assert has_positive_plan_max_cpo(adv) is expected


@pytest.mark.unit
def test_has_positive_plan_max_cpo_missing_attr() -> None:
    """16.1: отсутствие поля вообще → False (fail-closed для enable)."""
    assert has_positive_plan_max_cpo(SimpleNamespace()) is False


def _make_off_adv(*, max_cpo: object) -> SimpleNamespace:
    """OFF V3 paid кампания с заданным планом max CPO."""
    return SimpleNamespace(
        id=42,
        adv_id=4242,
        bot_active=True,
        automatic_version=3,
        max_price_for_order=max_cpo,
        card_ab_hold_mode=CardAbHoldMode.OFF.value,
        card_ab_hold_degraded=False,
        search_adv_id=None,
    )


def _make_session(adv: SimpleNamespace) -> tuple[MagicMock, MagicMock]:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=adv)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    return session, session_cm


def _make_query() -> MagicMock:
    query = MagicMock()
    query.answer = AsyncMock()
    msg = MagicMock()
    msg.answer = AsyncMock()
    query.message = msg
    query.bot = MagicMock()
    query.bot.send_message = AsyncMock()
    query.from_user = SimpleNamespace(id=1)
    return query


def _user_notice_text(query: MagicMock) -> str:
    """Текст user-visible notice (message.answer / bot.send_message)."""
    if query.message is not None and getattr(query.message, "answer", None):
        if query.message.answer.await_count > 0:
            args = query.message.answer.await_args.args
            if args:
                return str(args[0])
    send = getattr(getattr(query, "bot", None), "send_message", None)
    if send is not None and send.await_count > 0:
        args = send.await_args.args
        if len(args) >= 2:
            return str(args[1])
        if "text" in send.await_args.kwargs:
            return str(send.await_args.kwargs["text"])
    return ""


def _make_enable_success_mocks(
    adv: SimpleNamespace,
    session_cm: MagicMock,
) -> tuple[AsyncMock, MagicMock, SimpleNamespace]:
    refreshed = SimpleNamespace(
        **{
            **adv.__dict__,
            "card_ab_hold_mode": CardAbHoldMode.PENDING_SETUP.value,
        }
    )
    refresh_session = MagicMock()
    refresh_session.scalar = AsyncMock(return_value=refreshed)
    refresh_cm = MagicMock()
    refresh_cm.__aenter__ = AsyncMock(return_value=refresh_session)
    refresh_cm.__aexit__ = AsyncMock(return_value=None)
    start_epoch = AsyncMock(return_value=True)
    sm_side_effect = MagicMock(side_effect=[session_cm, refresh_cm])
    return start_epoch, sm_side_effect, refreshed


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("bad_max_cpo", [0, -1, None])
async def test_enable_blocked_when_max_cpo_missing_or_non_positive(
    bad_max_cpo: object,
) -> None:
    """16.1: max CPO missing/≤0 → mode OFF, ENTER не пишется, причина показана."""
    adv = _make_off_adv(max_cpo=bad_max_cpo)
    session, session_cm = _make_session(adv)
    query = _make_query()
    set_signal = AsyncMock()
    stats_eval = AsyncMock(return_value=(True, None))
    volume_eval = AsyncMock(
        return_value=LaunchViewVolumeEvaluation(
            outcome=LaunchViewVolumeOutcome.SUFFICIENT,
            total_views=9999,
        )
    )

    with (
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(handlers, "evaluate_ab_hold_enable_stats", new=stats_eval),
        patch.object(
            handlers, "evaluate_ab_hold_launch_view_volume", new=volume_eval
        ),
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(set_signal=set_signal),
        ),
    ):
        await handlers.enable_card_ab_hold(
            query, CardAbHoldEnable(adv_setting_original_id=42)
        )

    assert adv.card_ab_hold_mode == CardAbHoldMode.OFF.value
    session.commit.assert_not_awaited()
    set_signal.assert_not_awaited()
    # max-CPO gate — до freshness и объёмного soft-gate (decision §14a).
    stats_eval.assert_not_awaited()
    volume_eval.assert_not_awaited()
    query.answer.assert_not_awaited()
    assert "max CPO" in _user_notice_text(query)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_positive_max_cpo_proceeds_to_pending() -> None:
    """16.1 paired: max CPO > 0 (+ прочие gates) → PENDING_SETUP + Redis ENTER."""
    adv = _make_off_adv(max_cpo=100)
    session, session_cm = _make_session(adv)
    query = _make_query()
    set_signal = AsyncMock()
    start_epoch, sm_side_effect, refreshed = _make_enable_success_mocks(
        adv, session_cm
    )

    with (
        patch.object(handlers, "sm", sm_side_effect),
        patch.object(handlers, "start_epoch_on_enable", start_epoch),
        patch.object(
            handlers,
            "evaluate_ab_hold_enable_stats",
            new=AsyncMock(return_value=(True, None)),
        ),
        patch.object(
            handlers,
            "evaluate_ab_hold_launch_view_volume",
            new=AsyncMock(
                return_value=LaunchViewVolumeEvaluation(
                    outcome=LaunchViewVolumeOutcome.SUFFICIENT,
                    total_views=9999,
                )
            ),
        ),
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(set_signal=set_signal),
        ),
        patch.object(
            handlers,
            "CardAbHoldLastAbortRedisCache",
            return_value=MagicMock(get_abort=AsyncMock(return_value=None)),
        ),
    ):
        await handlers.enable_card_ab_hold(
            query, CardAbHoldEnable(adv_setting_original_id=42)
        )

    start_epoch.assert_awaited_once()
    assert refreshed.card_ab_hold_mode == CardAbHoldMode.PENDING_SETUP.value
    set_signal.assert_awaited_once()


@pytest.mark.unit
def test_max_cpo_message_mentions_max_cpo_and_within_alert_limit() -> None:
    """16.1: причина называет max CPO и умещается в лимит answerCallbackQuery."""
    msg = card_ab_hold_requires_max_cpo_message()
    assert "max CPO" in msg
    assert len(msg) <= 200


# --- 16.3: actionable PENDING status (decision §14b) ---


@pytest.mark.unit
@pytest.mark.parametrize(
    ("block_kind", "needle"),
    [
        (CardAbHoldSetupBlockKind.MISSING_MAX_CPO, "план max CPO"),
        (CardAbHoldSetupBlockKind.EMPTY_ALLOWED_SET, "нет подходящих ключей"),
        ("missing_max_cpo", "план max CPO"),
    ],
)
def test_setup_block_reason_line_actionable(
    block_kind: CardAbHoldSetupBlockKind | str, needle: str
) -> None:
    """16.3: известная причина блока → конкретный actionable-текст + действие."""
    line = setup_block_reason_line(block_kind)
    assert line is not None
    assert needle in line
    assert "отключите A/B Hold" in line


@pytest.mark.unit
@pytest.mark.parametrize("unknown", [None, "totally_unknown"])
def test_setup_block_reason_line_none_for_transient(unknown: str | None) -> None:
    """16.3: неизвестная/транзиентная причина → None (допустим generic)."""
    assert setup_block_reason_line(unknown) is None


@pytest.mark.unit
def test_pending_status_surfaces_block_reason_not_generic() -> None:
    """16.3: PENDING + детерминированный блок → actionable-причина, не «Подготовка…»."""
    status = build_enter_poll_status_lines(
        mode=CardAbHoldMode.PENDING_SETUP,
        abort_safe=None,
        abort_can_continue=None,
        block_kind=CardAbHoldSetupBlockKind.EMPTY_ALLOWED_SET,
    )
    assert "нет подходящих ключей" in status
    assert "Подготовка…" not in status
    assert "не запускайте A/B-тест" in status
    assert "можно запускать a/b" not in status.lower()


@pytest.mark.unit
def test_pending_status_generic_when_no_block() -> None:
    """16.3: PENDING без причины (транзиент) → generic «Подготовка…» допустим."""
    status = build_enter_poll_status_lines(
        mode=CardAbHoldMode.PENDING_SETUP,
        abort_safe=None,
        abort_can_continue=None,
        block_kind=None,
    )
    assert "Подготовка…" in status
    assert "не запускайте A/B-тест" in status


@pytest.mark.unit
def test_active_status_unaffected_by_block_kind() -> None:
    """16.3: ready-to-test — только ACTIVE; block_kind не влияет на ACTIVE ready."""
    status = build_enter_poll_status_lines(
        mode=CardAbHoldMode.ACTIVE,
        abort_safe=None,
        abort_can_continue=None,
        block_kind=CardAbHoldSetupBlockKind.EMPTY_ALLOWED_SET,
    )
    assert "Можно запускать A/B-тесты" in status


@pytest.mark.unit
def test_block_reason_status_within_telegram_limit() -> None:
    """16.3: worst-case PENDING+block статус в пределах лимита sendMessage."""
    for kind in CardAbHoldSetupBlockKind:
        status = build_enter_poll_status_lines(
            mode=CardAbHoldMode.PENDING_SETUP,
            abort_safe=True,
            abort_can_continue=True,
            block_kind=kind,
        )
        screen = f"{handlers._INSTRUCTION}\n{status}"
        assert len(screen) <= _TG_MESSAGE_TEXT_MAX
        assert "{" not in screen and "}" not in screen


# --- 16.4: process_ab_setup writes / clears the deterministic block reason ---


def _setup_complex_adv(*, max_cpo: object) -> SimpleNamespace:
    adv_setting = SimpleNamespace(
        id=555,
        adv_id=9,  # AdvSettingRedisCache key (ENTER common-bid reset)
        nmids=[101],
        max_price_for_order=max_cpo,
        card_ab_hold_mode="pending_setup",
        card_ab_hold_allowed_phrases_snapshot=None,
        card_ab_hold_degraded=False,
    )
    return SimpleNamespace(
        adv_id=9,
        shop_id=1,
        card_ab_hold_mode="pending_setup",
        adv_setting=adv_setting,
        search_adv=None,
    )


async def _run_setup(
    *,
    keywords: list[SimpleNamespace],
    max_cpo: object,
) -> tuple[MagicMock, AsyncMock, SimpleNamespace]:
    """Прогнать process_ab_setup с mocked lock/enforce/apply/block-cache."""
    complex_adv = _setup_complex_adv(max_cpo=max_cpo)
    complex_adv.get_keywords = AsyncMock(return_value=keywords)

    lock_mgr = MagicMock()
    lock_mgr.acquire = AsyncMock(return_value=True)
    lock_mgr.release = AsyncMock(return_value=None)

    mgr = MagicMock()
    mgr.enforce_frozen_allowed_set = AsyncMock(
        return_value={"targets": 1, "written": 0, "cap_exceeded": []}
    )
    container = MagicMock()
    container.minus_phrase_manager.return_value = mgr

    block_cache = MagicMock()
    block_cache.set_block = AsyncMock()
    block_cache.clear = AsyncMock()
    apply_mock = AsyncMock(return_value=(1, 0))

    with (
        patch(
            f"{_PIPELINES}.CardAbHoldSignalRedisCache",
            MagicMock(return_value=SimpleNamespace(client=MagicMock())),
        ),
        patch(
            f"{_PIPELINES}.CardAbHoldSetupBlockRedisCache",
            MagicMock(return_value=block_cache),
        ),
        patch(f"{_PIPELINES}.RedisLockManager", MagicMock(return_value=lock_mgr)),
        patch(
            f"{_PIPELINES}.MinusPhraseManagerContainer",
            MagicMock(return_value=container),
        ),
        patch(f"{_PIPELINES}.apply_ab_hold_setup_mutations", apply_mock),
        # Isolate setup body from §19 ENTER common-bid Redis/WB (not under test).
        patch(
            f"{_PIPELINES}.ensure_search_common_bid_reset_on_enter",
            new_callable=AsyncMock,
        ),
    ):
        await process_ab_setup(
            complex_adv,  # type: ignore[arg-type]
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
        )
    return block_cache, apply_mock, complex_adv


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_missing_max_cpo_sets_block_reason() -> None:
    """16.4: план max CPO ≤ 0 на тике → block-причина MISSING_MAX_CPO, не ACTIVE."""
    block_cache, apply_mock, complex_adv = await _run_setup(
        keywords=[SimpleNamespace(status=KeywordStatus.GOOD, text="good1")],
        max_cpo=0,
    )
    block_cache.set_block.assert_awaited_once()
    snapshot = block_cache.set_block.await_args.args[0]
    assert snapshot.kind == CardAbHoldSetupBlockKind.MISSING_MAX_CPO
    apply_mock.assert_not_awaited()
    assert (
        complex_adv.adv_setting.card_ab_hold_mode
        == CardAbHoldMode.PENDING_SETUP.value
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_empty_allowed_set_sets_block_reason() -> None:
    """16.4: все ключи BAD → block-причина EMPTY_ALLOWED_SET, mode остаётся PENDING."""
    block_cache, apply_mock, complex_adv = await _run_setup(
        keywords=[SimpleNamespace(status=KeywordStatus.BAD, text="bad1")],
        max_cpo=100,
    )
    block_cache.set_block.assert_awaited_once()
    snapshot = block_cache.set_block.await_args.args[0]
    assert snapshot.kind == CardAbHoldSetupBlockKind.EMPTY_ALLOWED_SET
    apply_mock.assert_not_awaited()
    assert (
        complex_adv.adv_setting.card_ab_hold_mode
        == CardAbHoldMode.PENDING_SETUP.value
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_success_clears_block_reason() -> None:
    """16.4: успешный setup → ACTIVE и снятие block-причины (не set)."""
    block_cache, apply_mock, complex_adv = await _run_setup(
        keywords=[SimpleNamespace(status=KeywordStatus.GOOD, text="good1")],
        max_cpo=100,
    )
    apply_mock.assert_awaited_once()
    block_cache.clear.assert_awaited_once()
    block_cache.set_block.assert_not_awaited()
    assert complex_adv.adv_setting.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value


# --- 16.4 reader: screen status surfaces the block reason for PENDING ---


@pytest.mark.unit
@pytest.mark.asyncio
async def test_screen_status_text_surfaces_block_for_pending() -> None:
    """16.4 reader: PENDING → actionable-причина из Redis-канала блока."""
    adv = SimpleNamespace(card_ab_hold_mode="pending_setup", card_ab_hold_degraded=False)
    block = SimpleNamespace(kind=CardAbHoldSetupBlockKind.EMPTY_ALLOWED_SET)
    with patch.object(
        handlers,
        "CardAbHoldSetupBlockRedisCache",
        return_value=MagicMock(get_block=AsyncMock(return_value=block)),
    ):
        text = await handlers._screen_status_text(
            adv,  # type: ignore[arg-type]
            CardAbHoldMode.PENDING_SETUP,
        )
    assert "нет подходящих ключей" in text
    assert "Подготовка…" not in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_screen_status_text_plain_for_non_pending() -> None:
    """16.4 reader: не-PENDING → краткий статус без обращения к block-каналу."""
    adv = SimpleNamespace(card_ab_hold_mode="off", card_ab_hold_degraded=False)
    block_cls = MagicMock()
    with patch.object(handlers, "CardAbHoldSetupBlockRedisCache", block_cls):
        text = await handlers._screen_status_text(
            adv,  # type: ignore[arg-type]
            CardAbHoldMode.OFF,
        )
    assert text == "Статус: off"
    block_cls.assert_not_called()


# --- 16.5: EXIT recovery from stuck PENDING + no owned auto-abort (MVP) ---


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exit_from_pending_recovers_to_off_and_clears_block() -> None:
    """16.5: EXIT из зависшего PENDING → OFF, ordinary снова eligible, block снят."""
    adv = SimpleNamespace(
        id=42,
        adv_id=4242,
        bot_active=True,
        wb_cabinet_id=7,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_allowed_phrases_snapshot=["good1"],
    )
    session, session_cm = _make_session(adv)
    query = _make_query()
    signal_clear = AsyncMock()
    block_clear = AsyncMock()
    enter_reset_clear = AsyncMock()
    ownership = AsyncMock(return_value=SimpleNamespace(id=11))

    with (
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(
            handlers,
            "get_wb_user_cabinet_for_adv_and_telegram",
            new=ownership,
        ),
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(clear=signal_clear),
        ),
        patch.object(
            handlers,
            "CardAbHoldSetupBlockRedisCache",
            return_value=MagicMock(clear=block_clear),
        ),
        patch.object(
            handlers,
            "CardAbHoldCommonBidEnterResetRedisCache",
            return_value=MagicMock(clear=enter_reset_clear),
        ),
    ):
        await handlers.disable_card_ab_hold(
            query, CardAbHoldDisable(adv_setting_original_id=42)
        )

    assert adv.card_ab_hold_mode == CardAbHoldMode.OFF.value
    # ordinary structural automation снова eligible после EXIT.
    assert is_ab_hold_structural_freeze(adv.card_ab_hold_mode) is False
    session.commit.assert_awaited()
    signal_clear.assert_awaited_once()
    block_clear.assert_awaited_once()
    enter_reset_clear.assert_awaited_once()


@pytest.mark.unit
def test_mvp_has_no_owned_auto_abort_timestamp_field() -> None:
    """16.5: MVP не вводит watchdog — нет durable ``pending_since`` поля (decision §14c).

    Owned авто-abort зависшего PENDING = SHOULD/future; MVP-контракт держится на
    actionable-причине + всегда доступном EXIT, без новой PG-миграции.
    """
    assert not hasattr(AdvSetting, "card_ab_hold_pending_since")
    assert not hasattr(AdvSetting, "card_ab_hold_pending_at")
