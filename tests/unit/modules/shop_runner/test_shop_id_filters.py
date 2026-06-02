"""Unit-тесты фильтрации shop_id для shop-runner."""

import os
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.shop_runner.shop_id_filters import (
    apply_shop_id_filters,
    filter_shop_ids,
    is_shop_id_allowed,
)
from app.settings.settings_master import Settings


def _compile_where_clause(stmt) -> str:
    return str(
        stmt.compile(compile_kwargs={"literal_binds": True})
    ).lower()


@pytest.mark.unit
def test_apply_shop_id_filters_no_lists() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SHOP_FILTER_LIST", None)
        os.environ.pop("SHOP_EXCLUDE_LIST", None)
        stmt = select(WBCabinet.shop_id).where(WBCabinet.active.is_(True))
        filtered = apply_shop_id_filters(stmt, WBCabinet.shop_id)
        sql = _compile_where_clause(filtered)
    assert " in " not in sql
    assert " not in " not in sql


@pytest.mark.unit
def test_apply_shop_id_filters_whitelist_only() -> None:
    with patch.dict(
        os.environ,
        {"SHOP_FILTER_LIST": "shop_a, shop_b", "SHOP_EXCLUDE_LIST": ""},
        clear=False,
    ):
        stmt = select(WBCabinet.shop_id)
        filtered = apply_shop_id_filters(stmt, WBCabinet.shop_id)
        sql = _compile_where_clause(filtered)
    assert "shop_a" in sql and "shop_b" in sql
    assert " in " in sql
    assert " not in " not in sql


@pytest.mark.unit
def test_apply_shop_id_filters_exclude_only() -> None:
    with patch.dict(
        os.environ,
        {"SHOP_EXCLUDE_LIST": "shop_x,shop_y"},
        clear=False,
    ):
        os.environ.pop("SHOP_FILTER_LIST", None)
        stmt = select(WBCabinet.shop_id)
        filtered = apply_shop_id_filters(stmt, WBCabinet.shop_id)
        sql = _compile_where_clause(filtered)
    assert "shop_x" in sql and "shop_y" in sql
    assert " not in " in sql


@pytest.mark.unit
def test_apply_shop_id_filters_whitelist_and_exclude() -> None:
    with patch.dict(
        os.environ,
        {
            "SHOP_FILTER_LIST": "shop_a,shop_b",
            "SHOP_EXCLUDE_LIST": "shop_b,shop_c",
        },
        clear=False,
    ):
        stmt = select(WBCabinet.shop_id)
        filtered = apply_shop_id_filters(stmt, WBCabinet.shop_id)
        sql = _compile_where_clause(filtered)
    assert "shop_a" in sql and "shop_b" in sql
    assert "shop_c" in sql
    assert " in " in sql
    assert " not in " in sql


@pytest.mark.unit
def test_settings_shop_exclude_list_parsing() -> None:
    settings = Settings()
    with patch.dict(
        os.environ,
        {"SHOP_EXCLUDE_LIST": " id1 , ,id2, "},
        clear=False,
    ):
        assert settings.SHOP_EXCLUDE_LIST == ["id1", "id2"]


@pytest.mark.unit
def test_is_shop_id_allowed_whitelist_and_exclude() -> None:
    with patch.dict(
        os.environ,
        {
            "SHOP_FILTER_LIST": "shop_a,shop_b",
            "SHOP_EXCLUDE_LIST": "shop_b",
        },
        clear=False,
    ):
        assert is_shop_id_allowed("shop_a") is True
        assert is_shop_id_allowed("shop_b") is False
        assert is_shop_id_allowed("shop_c") is False
        assert filter_shop_ids(["shop_a", "shop_b", "shop_c"]) == ["shop_a"]


@pytest.mark.unit
def test_is_shop_id_allowed_no_lists() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SHOP_FILTER_LIST", None)
        os.environ.pop("SHOP_EXCLUDE_LIST", None)
        assert is_shop_id_allowed("any") is True


@pytest.mark.unit
def test_settings_shop_filter_list_skips_empty_tokens() -> None:
    settings = Settings()
    with patch.dict(
        os.environ,
        {"SHOP_FILTER_LIST": "a,,b,"},
        clear=False,
    ):
        assert settings.SHOP_FILTER_LIST == ["a", "b"]
