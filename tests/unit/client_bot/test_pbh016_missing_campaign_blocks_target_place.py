"""FINDING-PBH-016 RED: missing AdvSetting must block keyword target_place write.

Invariant ``INV/BUGCASE-PBH-015/missing-campaign-blocks-mutators`` residual after
root FINDING-PBH-015 (add_white_phrases mode-None stop):
``keyword_target_place_value`` gates only with
``if adv_setting is not None and is_ab_hold_structural_freeze(...)``.
When ``KeywordSetting.adv_setting`` is ``None``, the Hold/campaign gate is
skipped and the handler still assigns ``keyword_setting.target_place`` and
``session.commit()`` — missing campaign treated as pass-through (Forbidden).

Regression: missing AdvSetting → no target_place write + campaign-not-found stop.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.keyword_settings import (
    keyword_target_place_value,
)

_HANDLER = "app.client_bot.user_interface.handlers.keyword_settings"
CAMPAIGN_NOT_FOUND_MSG = "Кампания не найдена."


def _keyword_setting_missing_campaign(*, target_place: int = 5) -> SimpleNamespace:
    """KeywordSetting row whose AdvSetting relation is missing (None)."""
    return SimpleNamespace(
        id=1,
        target_place=target_place,
        adv_setting=None,
    )


def _session_with_keyword(keyword: SimpleNamespace) -> AsyncMock:
    """Session mock returning ``keyword`` from execute().scalar_one_or_none()."""
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=keyword))
    )
    session.commit = AsyncMock()
    return session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keyword_target_place_blocks_when_campaign_missing() -> None:
    """Missing AdvSetting → target_place MUST NOT write; campaign-not-found UX."""
    keyword = _keyword_setting_missing_campaign(target_place=5)
    session = _session_with_keyword(keyword)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    message = SimpleNamespace(
        chat=SimpleNamespace(id=42),
        text="10",
        from_user=SimpleNamespace(id=7),
    )
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "keyword_setting_for_target_place": 1,
            "last_keyword_setting_page": 1,
        }
    )
    bot = AsyncMock()

    updated_cls = MagicMock(return_value=AsyncMock())
    keyword_msg_cls = MagicMock(return_value=AsyncMock())

    with (
        patch(f"{_HANDLER}._sm", mock_sm),
        patch(f"{_HANDLER}.messages.KeywordTargetPlaceUpdated", updated_cls),
        patch(f"{_HANDLER}.messages.KeywordSettingMessage", keyword_msg_cls),
    ):
        await keyword_target_place_value(message, bot, state)

    assert keyword.target_place == 5
    session.commit.assert_not_called()
    updated_cls.assert_not_called()
    keyword_msg_cls.assert_not_called()
    bot.send_message.assert_awaited_with(42, CAMPAIGN_NOT_FOUND_MSG)
    state.set_state.assert_awaited()
