"""Tests for single_run decorator and make_key (hashable kwargs)."""

import pytest

from app.modules.shop_runner.service_manager.wb_shop_data_manager.single_run_decorator import (
    make_key,
)


def test_make_key_with_dict_kwargs_does_not_raise() -> None:
    """Passing dict kwargs (e.g. search_adv_bids_override) must not raise unhashable type."""
    # search_adv_bids_override: dict[int, dict[int, int]]
    kwargs = {"search_adv_bids_override": {1: {100: 50, 200: 60}, 2: {100: 70}}}
    key = make_key("get_wb_advs_dto", ([],), kwargs)
    assert "get_wb_advs_dto" in key
    assert isinstance(key, str)


def test_make_key_same_dict_kwargs_same_key() -> None:
    """Same dict content produces same key for deduplication."""
    kwargs = {"search_adv_bids_override": {1: {100: 50}, 2: {100: 70}}}
    key1 = make_key("get_wb_advs_dto", ([],), kwargs)
    key2 = make_key("get_wb_advs_dto", ([],), {"search_adv_bids_override": {2: {100: 70}, 1: {100: 50}}})
    assert key1 == key2


def test_make_key_different_dict_kwargs_different_key() -> None:
    """Different dict content produces different key."""
    key1 = make_key("get_wb_advs_dto", ([],), {"search_adv_bids_override": {1: {100: 50}}})
    key2 = make_key("get_wb_advs_dto", ([],), {"search_adv_bids_override": {1: {100: 60}}})
    assert key1 != key2


def test_make_key_none_override() -> None:
    """None as kwargs value is hashable."""
    key = make_key("get_wb_advs_dto", ([],), {"search_adv_bids_override": None})
    assert "get_wb_advs_dto" in key
