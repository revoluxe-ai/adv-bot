from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.keywords_manager.keywords_manager import KeywordsManager
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus


def _kw(
    *,
    views: int = 10,
    hard_status: int = 1,
    status: KeywordStatus = KeywordStatus.BAD,
    relevant: bool = True,
    above_rec_conversion: bool | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        views=views,
        hard_status=hard_status,
        status=status,
        relevant=relevant,
        above_rec_conversion=above_rec_conversion,
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
