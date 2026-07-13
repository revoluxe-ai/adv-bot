"""Тесты pack/unpack callback экрана V3-решения по ключу."""

from __future__ import annotations

import pytest

from app.client_bot.user_interface.views.callbacks import (
    KeywordV3DecisionTraceBack,
    KeywordV3DecisionTraceOpen,
    KeywordV3DecisionTraceRefresh,
)


@pytest.mark.unit
def test_open_callback_pack_unpack() -> None:
    cb = KeywordV3DecisionTraceOpen(
        keyword_setting_original_id=42,
        page=3,
    )
    packed = cb.pack()
    unpacked = KeywordV3DecisionTraceOpen.unpack(packed)
    assert unpacked.keyword_setting_original_id == 42
    assert unpacked.page == 3


@pytest.mark.unit
def test_refresh_callback_pack_unpack() -> None:
    cb = KeywordV3DecisionTraceRefresh(
        keyword_setting_original_id=7,
        page=2,
    )
    packed = cb.pack()
    unpacked = KeywordV3DecisionTraceRefresh.unpack(packed)
    assert unpacked.keyword_setting_original_id == 7
    assert unpacked.page == 2


@pytest.mark.unit
def test_back_callback_pack_unpack() -> None:
    cb = KeywordV3DecisionTraceBack(
        keyword_setting_original_id=15,
        page=5,
    )
    packed = cb.pack()
    unpacked = KeywordV3DecisionTraceBack.unpack(packed)
    assert unpacked.keyword_setting_original_id == 15
    assert unpacked.page == 5


@pytest.mark.unit
def test_open_callback_default_page() -> None:
    cb = KeywordV3DecisionTraceOpen(keyword_setting_original_id=1)
    assert cb.page == 1
