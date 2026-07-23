"""Unit-тесты пагинации confirm-flow A/B Hold (§24.1, ux contract §9)."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_pagination import (
    PAGE_SIZE,
    paginate,
)


@pytest.mark.unit
def test_page_size_is_ten() -> None:
    assert PAGE_SIZE == 10


@pytest.mark.unit
def test_paginate_single_page() -> None:
    items = [f"kw{i}" for i in range(7)]
    slice_items, page, total_pages = paginate(items, 0)
    assert slice_items == items
    assert page == 0
    assert total_pages == 1


@pytest.mark.unit
def test_paginate_second_page() -> None:
    items = [f"kw{i}" for i in range(15)]
    slice_items, page, total_pages = paginate(items, 1)
    assert slice_items == items[10:15]
    assert page == 1
    assert total_pages == 2


@pytest.mark.unit
def test_paginate_clamps_page_bounds() -> None:
    items = [f"kw{i}" for i in range(25)]
    _, page_neg, total = paginate(items, -3)
    assert page_neg == 0
    assert total == 3
    _, page_over, _ = paginate(items, 99)
    assert page_over == 2


@pytest.mark.unit
def test_paginate_empty_list_still_one_page() -> None:
    slice_items, page, total_pages = paginate([], 0)
    assert slice_items == []
    assert page == 0
    assert total_pages == 1
