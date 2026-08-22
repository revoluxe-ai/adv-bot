"""CTR-boost path: Redis set_auto_block_status after injectable CH seam.

EXTERNAL_CALL_COVERAGE gap (REDIS / TEST_ONLY):
``change_keyword_hard_status`` CTR branch must call
``redis_manager.set_auto_block_status`` after CH boost mutates added_clicks.

Handler integration tests ниже skip: CTR-boost path в ``keyword_settings`` отложен
(см. комментарий у ``change_keyword_hard_status``); тесты сохранены для restore.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.keyword_settings import (
    change_keyword_hard_status,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)

_HANDLER = "app.client_bot.user_interface.handlers.keyword_settings"

CTR_BOOST_HANDLER_SKIP = pytest.mark.skip(
    reason=(
        "CTR-boost deferred: change_keyword_hard_status CH/Redis path disabled; "
        "test kept for restore"
    ),
)


def _session_with_keyword(keyword: SimpleNamespace) -> AsyncMock:
    """AsyncSession mock returning ``keyword`` from ``session.execute``."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar = MagicMock(return_value=keyword)
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    return session


@pytest.mark.unit
@pytest.mark.asyncio
@CTR_BOOST_HANDLER_SKIP
async def test_ctr_boost_path_calls_set_auto_block_status() -> None:
    """hard_status=-1 CTR path → Redis set_auto_block_status(False) once."""
    adv = SimpleNamespace(
        id=1,
        adv_id=10,
        search_adv_id=None,
        card_ab_hold_mode=CardAbHoldMode.OFF.value,
        automatic_version=3,
        strategy=None,
    )
    keyword = SimpleNamespace(
        id=7,
        hard_status=1,
        text="kw",
        added_clicks=0,
        added_views=100,
        adv_setting=adv,
    )
    session = _session_with_keyword(keyword)

    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    callback = MagicMock()
    callback.message = SimpleNamespace(chat=SimpleNamespace(id=99))
    callback.from_user = SimpleNamespace(id=1)
    callback_data = SimpleNamespace(
        new_hard_status=-1,
        keyword_setting_original_id=7,
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"last_keyword_setting_page": 1})

    typing_cm = MagicMock()
    typing_cm.__aenter__ = AsyncMock(return_value=None)
    typing_cm.__aexit__ = AsyncMock(return_value=None)

    redis_set = AsyncMock()
    ch_cm = MagicMock()
    ch_cm.__aenter__ = AsyncMock(return_value=object())
    ch_cm.__aexit__ = AsyncMock(return_value=None)

    keyword_msg = AsyncMock()

    with (
        patch(f"{_HANDLER}._sm", mock_sm),
        patch(f"{_HANDLER}.ChatActionSender.typing", return_value=typing_cm),
        patch(f"{_HANDLER}.get_clickhouse_client", return_value=ch_cm),
        patch(
            f"{_HANDLER}.data_manager.get_min_ctr",
            new=AsyncMock(return_value=0.01),
            create=True,
        ),
        patch(
            f"{_HANDLER}.apply_keyword_ctr_boost_with_client",
            new=AsyncMock(return_value=1),
        ),
        patch(f"{_HANDLER}.redis_manager.set_auto_block_status", redis_set),
        patch(
            f"{_HANDLER}.messages.KeywordSettingMessage",
            MagicMock(return_value=keyword_msg),
        ),
    ):
        await change_keyword_hard_status(callback, callback_data, bot, state)

    redis_set.assert_awaited_once_with(7, False)
    session.commit.assert_awaited()
