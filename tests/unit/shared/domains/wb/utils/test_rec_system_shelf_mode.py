"""Тесты режима полок и предупреждения по кликам."""

from unittest.mock import AsyncMock, patch

import pytest

from app.shared.domains.wb.utils.rec_system_shelf_mode import (
    is_rec_system_shelf_mode_operational,
    should_show_clicks_warning,
    warning_suffix,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("rec_system", "active_status", "cost_active", "expected"),
    [
        (False, "started", True, False),
        (True, "paused", True, False),
        (True, "started", False, False),
        (True, "started", None, False),
        (True, "started", True, True),
    ],
)
@pytest.mark.asyncio
async def test_is_rec_system_shelf_mode_operational_table(
    rec_system: bool,
    active_status: str,
    cost_active: bool | None,
    expected: bool,
) -> None:
    adv = AsyncMock()
    adv.rec_system_mode = rec_system
    adv.active_status = active_status
    with patch(
        "app.shared.domains.wb.utils.rec_system_shelf_mode.is_auto_campaign_active",
        new=AsyncMock(return_value=cost_active),
    ):
        assert await is_rec_system_shelf_mode_operational(adv) is expected


@pytest.mark.parametrize(
    ("shelves_operational", "adv", "organic", "shelf", "want_warn"),
    [
        (True, 5, 100, 50, True),
        (True, 50, 100, 50, False),
        (False, 5, 100, 50, True),
        (False, 100, 100, 5, False),
        (False, 99, 100, 5, True),
    ],
)
def test_should_show_clicks_warning_branches(
    shelves_operational: bool,
    adv: int,
    organic: int,
    shelf: int,
    want_warn: bool,
) -> None:
    got = should_show_clicks_warning(
        shelves_operational=shelves_operational,
        adv_clicks=adv,
        organic_clicks=organic,
        shelf_clicks=shelf,
    )
    assert got is want_warn


def test_should_show_clicks_warning_equal_no_warning() -> None:
    assert (
        should_show_clicks_warning(
            shelves_operational=True,
            adv_clicks=10,
            organic_clicks=5,
            shelf_clicks=10,
        )
        is False
    )
    assert (
        should_show_clicks_warning(
            shelves_operational=False,
            adv_clicks=10,
            organic_clicks=10,
            shelf_clicks=100,
        )
        is False
    )


@pytest.mark.parametrize(
    ("show", "expected"),
    [(True, " ⚠"), (False, "")],
)
def test_warning_suffix(show: bool, expected: str) -> None:
    assert warning_suffix(show) == expected
