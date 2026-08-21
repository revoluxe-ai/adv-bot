"""RED: public EXIT must fail-closed when Telegram actor id is missing/invalid.

Invariant (ROOT-001 / BUGCASE-CAH-EXIT-FAIL-OPEN):
``disable_card_ab_hold`` must not pass a missing actor into
``disable_card_ab_hold_in_session`` in a way that skips ownership and still
performs mode→OFF / commit. When ``_callback_actor_id`` yields ``None``,
public EXIT must reject without PG mutation.

Note: ``disable_card_ab_hold_in_session(..., telegram_user_id=None)`` remains
intentional for internal session-seam callers; this suite targets the public
handler path that currently forwards ``None`` from ``_callback_actor_id``.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldDisable,
)


def _make_active_adv() -> SimpleNamespace:
    """AdvSetting double in ACTIVE A/B Hold with cabinet ownership surface."""
    return SimpleNamespace(
        id=42,
        adv_id=4242,
        bot_active=True,
        wb_cabinet_id=7,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        card_ab_hold_allowed_phrases_snapshot={"allowed": ["alpha"]},
        card_ab_hold_phase=None,
        card_ab_hold_generation=0,
        card_ab_hold_sync_status=None,
        card_ab_hold_degraded=False,
        card_ab_hold_emergency_educated=False,
        card_ab_hold_emergency_latch=False,
    )


def _make_session(adv: SimpleNamespace) -> tuple[MagicMock, MagicMock]:
    """WRITE session + async context manager for ``sm(read_only=False)``."""
    session = MagicMock()
    session.scalar = AsyncMock(return_value=adv)
    session.commit = AsyncMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    return session, session_cm


def _make_query(*, from_user: object | None) -> MagicMock:
    """CallbackQuery double; ``from_user`` drives ``_callback_actor_id``."""
    query = MagicMock()
    query.answer = AsyncMock()
    query.message = MagicMock(answer=AsyncMock())
    query.bot = MagicMock(send_message=AsyncMock())
    query.from_user = from_user
    return query


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "from_user",
    [
        None,
        SimpleNamespace(id=None),
        SimpleNamespace(id="not-an-int"),
        SimpleNamespace(id=True),
    ],
    ids=["no_from_user", "id_none", "id_str", "id_bool"],
)
async def test_public_disable_rejects_missing_actor_before_commit(
    from_user: object | None,
) -> None:
    """Public EXIT must not mode→OFF when ``_callback_actor_id`` is None.

    Regression for ROOT-001: missing/invalid Telegram actor must fail-closed
    (reject / notify) without skipping ownership and committing EXIT.
    """
    adv = _make_active_adv()
    session, session_cm = _make_session(adv)
    query = _make_query(from_user=from_user)
    ownership = AsyncMock(return_value=SimpleNamespace(id=11))
    assert handlers._callback_actor_id(query) is None

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
        patch.object(handlers, "_edit_screen", new_callable=AsyncMock) as edit_screen,
        patch.object(handlers, "is_card_ab_hold_ui_visible", return_value=True),
    ):
        await handlers.disable_card_ab_hold(
            query, CardAbHoldDisable(adv_setting_original_id=42)
        )

    assert adv.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value, (
        "fail-open: public EXIT turned mode OFF despite missing/invalid actor"
    )
    assert adv.card_ab_hold_allowed_phrases_snapshot == {"allowed": ["alpha"]}
    session.commit.assert_not_awaited()
    ownership.assert_not_awaited()
    edit_screen.assert_not_awaited()
