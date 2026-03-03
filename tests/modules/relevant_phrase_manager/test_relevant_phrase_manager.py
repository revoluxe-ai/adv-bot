"""Unit tests for RelevantPhraseManager (black_phrases in Postgres)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.relevant_phrase_manager import RelevantPhraseManager


@pytest.fixture
def adv_with_black_phrases() -> MagicMock:
    adv = MagicMock(spec=AdvSetting)
    adv.id = 1
    adv.black_phrases = ["not:spam", "any:word1,word2"]
    return adv


@pytest.fixture
def adv_empty_black_phrases() -> MagicMock:
    adv = MagicMock(spec=AdvSetting)
    adv.id = 2
    adv.black_phrases = []
    return adv


@pytest.fixture
def adv_no_black_phrases_attr() -> MagicMock:
    adv = MagicMock(spec=AdvSetting)
    adv.id = 3
    del adv.black_phrases
    return adv


@pytest.mark.asyncio
async def test_get_relevant_template_data_returns_adv_black_phrases(
    adv_with_black_phrases: MagicMock,
) -> None:
    manager = RelevantPhraseManager(adv_with_black_phrases)
    result = await manager.get_relevant_template_data()
    assert result == ["not:spam", "any:word1,word2"]


@pytest.mark.asyncio
async def test_get_relevant_template_data_returns_empty_when_empty(
    adv_empty_black_phrases: MagicMock,
) -> None:
    manager = RelevantPhraseManager(adv_empty_black_phrases)
    result = await manager.get_relevant_template_data()
    assert result == []


@pytest.mark.asyncio
async def test_get_relevant_template_data_returns_empty_when_attr_missing(
    adv_no_black_phrases_attr: MagicMock,
) -> None:
    manager = RelevantPhraseManager(adv_no_black_phrases_attr)
    result = await manager.get_relevant_template_data()
    assert result == []


@pytest.mark.asyncio
async def test_update_black_phrases_persists_and_updates_keywords() -> None:
    from sqlalchemy.sql.dml import Update

    adv = MagicMock(spec=AdvSetting)
    adv.id = 10
    adv.black_phrases = []

    executed: list = []

    def execute_side_effect(stmt):
        executed.append(stmt)
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    session = MagicMock()
    session.execute = AsyncMock(side_effect=execute_side_effect)
    session.commit = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    sm_mock = MagicMock(return_value=cm)

    with patch(
        "app.modules.relevant_phrase_manager.relevant_phrase_manager.sm",
        sm_mock,
    ):
        manager = RelevantPhraseManager(adv)
        await manager.update_black_phrases(["phrase1", "not:phrase2"])

    assert len(executed) >= 1
    first_stmt = executed[0]
    assert isinstance(first_stmt, Update)
    # Check the update targets AdvSetting and sets black_phrases (stmt has .values)
    assert "advsetting" in str(first_stmt.table.name).lower() or "black_phrases" in str(first_stmt)
