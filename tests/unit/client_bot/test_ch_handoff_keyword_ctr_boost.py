"""Mock-only: CTR CH parent→child client handoff for hard_status=-1.

Доказывает injectable ``apply_keyword_ctr_boost_with_client``: parent открывает
``get_clickhouse_client()`` и передаёт client в child (не module-patch CH).

``test_change_keyword_hard_status_ctr_hands_off_ch_client`` skip: handler CTR path
отложен; unit-тесты ``apply_keyword_ctr_boost_with_client`` остаются активными.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers import keyword_settings
from app.client_bot.user_interface.handlers.keyword_settings import (
    KeywordHardStatusChangeOutcome,
    apply_keyword_ctr_boost_with_client,
)

_KS = "app.client_bot.user_interface.handlers.keyword_settings"

CTR_BOOST_HANDLER_SKIP = pytest.mark.skip(
    reason=(
        "CTR-boost deferred: change_keyword_hard_status CH/Redis path disabled; "
        "test kept for restore"
    ),
)


def _session_cm(session: MagicMock) -> MagicMock:
    """Async context manager yielding ``session``."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


def _client_cm(client: MagicMock) -> MagicMock:
    """Async context manager yielding CH ``client``."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.mark.unit
@pytest.mark.asyncio
@CTR_BOOST_HANDLER_SKIP
async def test_change_keyword_hard_status_ctr_hands_off_ch_client() -> None:
    """Parent CTR path → ``apply_keyword_ctr_boost_with_client(client, …)``."""
    fake_session = MagicMock(name="hs_write_session")
    fake_session.commit = AsyncMock()
    fake_client = MagicMock(name="ch_client")
    keyword = SimpleNamespace(
        id=42,
        text="платье",
        added_clicks=0,
        added_views=0,
    )
    adv = SimpleNamespace(adv_id=1001, search_adv_id=None)
    child_pg = AsyncMock(
        return_value=KeywordHardStatusChangeOutcome(
            kind="needs_ctr_boost",
            keyword_setting=keyword,
            adv_setting=adv,
        )
    )
    ch_child = AsyncMock(return_value=5)
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    callback = MagicMock()
    callback.message = MagicMock()
    callback.message.chat = MagicMock()
    callback.message.chat.id = 7
    callback.from_user = MagicMock()
    callback.from_user.id = 99
    callback_data = SimpleNamespace(
        new_hard_status=-1, keyword_setting_original_id=42
    )
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"last_keyword_setting_page": 1})
    bot = AsyncMock()
    typing_cm = MagicMock()
    typing_cm.__aenter__ = AsyncMock(return_value=None)
    typing_cm.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(f"{_KS}._sm", sm_mock),
        patch(f"{_KS}.change_keyword_hard_status_in_session", child_pg),
        patch(f"{_KS}.apply_keyword_ctr_boost_with_client", ch_child),
        patch(f"{_KS}.get_clickhouse_client", return_value=_client_cm(fake_client)),
        patch(f"{_KS}.data_manager.get_min_ctr", AsyncMock(return_value=0.05), create=True),
        patch(f"{_KS}.redis_manager.set_auto_block_status", AsyncMock()),
        patch(f"{_KS}.ChatActionSender.typing", return_value=typing_cm),
        patch(f"{_KS}.messages.KeywordSettingMessage", return_value=AsyncMock()),
    ):
        await keyword_settings.change_keyword_hard_status(
            callback, callback_data, bot, state
        )

    ch_child.assert_awaited_once_with(
        fake_client,
        keyword_setting=keyword,
        keyword_text="платье",
        adv_ids={1001},
        min_ctr=0.05,
    )
    fake_session.commit.assert_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_keyword_ctr_boost_with_client_mutates_added_clicks() -> None:
    """Child seam: CH stats → mutate ``added_clicks`` (min 1)."""
    keyword = SimpleNamespace(added_clicks=None, added_views=None)
    client = MagicMock(name="mock_ch")

    with patch(
        f"{_KS}.data_manager.get_keyword_statistic_clickhouse",
        AsyncMock(return_value=(10, 200, 0.0)),
    ) as stats:
        added = await apply_keyword_ctr_boost_with_client(
            client,
            keyword_setting=keyword,
            keyword_text="платье",
            adv_ids={1001},
            min_ctr=0.10,
            boost_percent=10,
        )

    stats.assert_awaited_once_with(client, "платье", {1001})
    # new_ctr = 0.11; 0.11 * 200 - 10 = 12 → add_clicks=12
    assert added == 12
    assert keyword.added_clicks == 12


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_keyword_ctr_boost_preserves_existing_added_clicks() -> None:
    """Existing ``added_clicks`` входят в CH baseline перед boost."""
    keyword = SimpleNamespace(added_clicks=5, added_views=0)
    client = MagicMock()

    with patch(
        f"{_KS}.data_manager.get_keyword_statistic_clickhouse",
        AsyncMock(return_value=(10, 100, 0.0)),
    ):
        added = await apply_keyword_ctr_boost_with_client(
            client,
            keyword_setting=keyword,
            keyword_text="x",
            adv_ids={1},
            min_ctr=0.20,
            boost_percent=10,
        )

    # clicks effective=15; new_ctr=0.22; 0.22*100-15=7 → add=7; total=12
    assert added == 7
    assert keyword.added_clicks == 12
