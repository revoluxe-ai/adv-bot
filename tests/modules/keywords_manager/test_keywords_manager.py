from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.keywords_manager.keywords_manager import KeywordsManager
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)


def _kw(
    *,
    views: int = 10,
    hard_status: int = 1,
    status: KeywordStatus = KeywordStatus.BAD,
    relevant: bool = True,
    above_rec_conversion: bool | None = None,
    reason: KeywordStatusReason | None = None,
    rating: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        views=views,
        hard_status=hard_status,
        status=status,
        relevant=relevant,
        above_rec_conversion=above_rec_conversion,
        reason=reason,
        rating=rating,
    )


@pytest.mark.asyncio
async def test_candidates_skip_below_rec_only_when_shelf_activation_allowed() -> None:
    manager = KeywordsManager()
    blocked = _kw(above_rec_conversion=False)
    allowed = _kw(above_rec_conversion=True)
    complex_adv = SimpleNamespace(
        auto_add_only_relevant_phrase=False,
        rec_system_promotion_mode_active=True,
        auto_adv_active_status=True,
        is_shelf_activation_allowed=True,
        get_keywords=AsyncMock(return_value=[blocked, allowed]),
    )

    result = await manager.get_candidates_to_white_list(complex_adv)
    assert result == [allowed]


@pytest.mark.asyncio
async def test_candidates_allow_below_rec_when_organic_above_shelf() -> None:
    manager = KeywordsManager()
    below_rec = _kw(above_rec_conversion=False)
    complex_adv = SimpleNamespace(
        auto_add_only_relevant_phrase=False,
        rec_system_promotion_mode_active=True,
        auto_adv_active_status=True,
        is_shelf_activation_allowed=False,
        get_keywords=AsyncMock(return_value=[below_rec]),
    )

    result = await manager.get_candidates_to_white_list(complex_adv)
    assert result == [below_rec]


@pytest.mark.asyncio
async def test_add_new_keyword_settings_only_relevant_templates_applied() -> None:
    manager = KeywordsManager()
    adv = MagicMock()
    adv.auto_add_only_relevant_phrase = True
    adv.relevant_phrases = [r"foo"]
    adv.black_phrases = ["."]  # must not force blacklist in this mode
    adv.id = 5
    complex_adv = MagicMock()
    complex_adv.original_adv_setting_id = 5
    complex_adv.adv_setting = adv

    session = MagicMock()
    session.add = MagicMock()

    with patch.object(
        KeywordsManager,
        "_KeywordsManager__get_exists_keyword_settings_text",
        new_callable=AsyncMock,
        return_value=(),
    ):
        await manager._add_new_keyword_settings_to_session(  # pyright: ignore[reportPrivateUsage]
            session, complex_adv, ["foobar"]
        )

    session.add.assert_called_once()
    kw = session.add.call_args[0][0]
    assert isinstance(kw, KeywordSetting)
    assert kw.hard_status == 1
    assert kw.relevant is True
    assert kw.text == "foobar"


@pytest.mark.asyncio
async def test_add_new_keyword_settings_black_templates_when_not_only_relevant() -> None:
    manager = KeywordsManager()
    adv = MagicMock()
    adv.auto_add_only_relevant_phrase = False
    adv.relevant_phrases = [r".*"]
    adv.black_phrases = ["spam"]
    adv.id = 6
    complex_adv = MagicMock()
    complex_adv.original_adv_setting_id = 6
    complex_adv.adv_setting = adv

    session = MagicMock()
    session.add = MagicMock()

    with patch.object(
        KeywordsManager,
        "_KeywordsManager__get_exists_keyword_settings_text",
        new_callable=AsyncMock,
        return_value=(),
    ):
        await manager._add_new_keyword_settings_to_session(  # pyright: ignore[reportPrivateUsage]
            session, complex_adv, ["spam", "ok"]
        )

    assert session.add.call_count == 2
    calls = [c.args[0] for c in session.add.call_args_list]
    by_text = {k.text: k for k in calls}
    assert by_text["spam"].hard_status == 0
    assert by_text["spam"].relevant is False
    assert by_text["ok"].hard_status == 1
    assert by_text["ok"].relevant is False
