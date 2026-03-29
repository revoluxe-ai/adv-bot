"""Unit tests for RelevantPhraseManager (black_phrases in Postgres)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.relevant_phrase_manager import RelevantPhraseManager


@pytest.fixture
def adv_with_black_phrases() -> MagicMock:
    adv = MagicMock(spec=AdvSetting)
    adv.id = 1
    adv.black_phrases = ["spam", r"cheap|discount"]
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
    assert result == ["spam", r"cheap|discount"]


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
        await manager.update_black_phrases(["phrase1", r"phrase2|alt"])

    assert len(executed) >= 1
    first_stmt = executed[0]
    assert isinstance(first_stmt, Update)
    # Check the update targets AdvSetting and sets black_phrases (stmt has .values)
    assert "advsetting" in str(first_stmt.table.name).lower() or "black_phrases" in str(
        first_stmt
    )


@pytest.fixture
def adv_with_relevant_phrases() -> MagicMock:
    adv = MagicMock(spec=AdvSetting)
    adv.id = 11
    adv.relevant_phrases = ["brand", r"летн"]
    return adv


@pytest.mark.asyncio
async def test_get_relevant_phrases_template_data_returns_list(
    adv_with_relevant_phrases: MagicMock,
) -> None:
    manager = RelevantPhraseManager(adv_with_relevant_phrases)
    result = await manager.get_relevant_phrases_template_data()
    assert result == ["brand", r"летн"]


@pytest.mark.asyncio
async def test_get_relevant_phrases_template_data_filters_non_str() -> None:
    adv = MagicMock(spec=AdvSetting)
    adv.id = 12
    adv.relevant_phrases = ["ok", 123, None, "x"]  # type: ignore[list-item]
    manager = RelevantPhraseManager(adv)
    result = await manager.get_relevant_phrases_template_data()
    assert result == ["ok", "x"]


@pytest.mark.asyncio
async def test_update_relevant_phrases_templates_persists() -> None:
    from sqlalchemy.sql.dml import Update

    adv = MagicMock(spec=AdvSetting)
    adv.id = 20
    adv.relevant_phrases = []

    executed: list = []

    def execute_side_effect(stmt: object) -> MagicMock:
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
        await manager.update_relevant_phrases_templates(["a", r"b|c"])

    assert len(executed) >= 1
    first_stmt = executed[0]
    assert isinstance(first_stmt, Update)
    stmt_str = str(first_stmt).lower()
    assert "relevant_phrases" in stmt_str or "advsetting" in stmt_str


def test_initial_flags_only_relevant_mode_match() -> None:
    adv = MagicMock(spec=AdvSetting)
    adv.auto_add_only_relevant_phrase = True
    adv.relevant_phrases = [r"foo"]
    adv.black_phrases = ["."]  # ignored in this mode
    hard, rel = RelevantPhraseManager.initial_flags_for_new_keyword("foobar", adv)
    assert hard == 1
    assert rel is True


def test_initial_flags_only_relevant_mode_no_match() -> None:
    adv = MagicMock(spec=AdvSetting)
    adv.auto_add_only_relevant_phrase = True
    adv.relevant_phrases = ["^exact$"]
    hard, rel = RelevantPhraseManager.initial_flags_for_new_keyword("not exact", adv)
    assert hard == 1
    assert rel is False


def test_initial_flags_black_mode_blacklisted() -> None:
    adv = MagicMock(spec=AdvSetting)
    adv.auto_add_only_relevant_phrase = False
    adv.black_phrases = ["spam"]
    adv.relevant_phrases = [r".*"]  # ignored when only black applies
    hard, rel = RelevantPhraseManager.initial_flags_for_new_keyword("spam", adv)
    assert hard == 0
    assert rel is False


def test_initial_flags_black_mode_not_blacklisted() -> None:
    adv = MagicMock(spec=AdvSetting)
    adv.auto_add_only_relevant_phrase = False
    adv.black_phrases = ["spam"]
    hard, rel = RelevantPhraseManager.initial_flags_for_new_keyword("good phrase", adv)
    assert hard == 1
    assert rel is False
