"""Unit-тесты guard-модуля DEBUG_CLUSTER_BID_TRACE."""

from __future__ import annotations

import logging

import pytest

from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.cluster_bid_trace import (
    format_error_detail,
    is_trace_cell,
    is_trace_enabled,
    log_cluster_bid_trace,
    reset_trace_config_for_tests,
)

_TRACE_ENV = {
    "DEBUG_CLUSTER_BID_TRACE": "1",
    "DEBUG_CLUSTER_BID_TRACE_SHOP_ID": "db28efff-f7a9-52f8-8342-f1a58f7d8ed3",
    "DEBUG_CLUSTER_BID_TRACE_ADV_ID": "32824944",
    "DEBUG_CLUSTER_BID_TRACE_SEARCH_ADV_ID": "29734515",
    "DEBUG_CLUSTER_BID_TRACE_NMID": "10749810",
    "DEBUG_CLUSTER_BID_TRACE_KS_ID": "17783715",
    "DEBUG_CLUSTER_BID_TRACE_KEY": "антивозрастной матирующий крем",
}


@pytest.fixture(autouse=True)
def _reset_trace_config() -> None:
    reset_trace_config_for_tests()


def _set_trace_env(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> None:
    env = {**_TRACE_ENV, **overrides}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    reset_trace_config_for_tests()


def test_trace_disabled_is_noop(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.delenv("DEBUG_CLUSTER_BID_TRACE", raising=False)
    reset_trace_config_for_tests()

    assert is_trace_enabled() is False
    assert is_trace_cell(shop_id=_TRACE_ENV["DEBUG_CLUSTER_BID_TRACE_SHOP_ID"], adv_id=32824944) is False

    with caplog.at_level(logging.INFO):
        log_cluster_bid_trace(
            step="tick_enter",
            shop_id=_TRACE_ENV["DEBUG_CLUSTER_BID_TRACE_SHOP_ID"],
            adv_id=32824944,
        )

    assert "[cluster_bid_trace]" not in caplog.text


def test_exact_match_allows_log(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    _set_trace_env(monkeypatch)

    assert is_trace_cell(
        shop_id="db28efff-f7a9-52f8-8342-f1a58f7d8ed3",
        adv_id=32824944,
        search_adv_id=29734515,
        nmid=10749810,
        ks_id=17783715,
        key="антивозрастной матирующий крем",
    )

    with caplog.at_level(logging.INFO):
        log_cluster_bid_trace(
            step="new_bid_calculate",
            shop_id="db28efff-f7a9-52f8-8342-f1a58f7d8ed3",
            adv_id=32824944,
            search_adv_id=29734515,
            nmid=10749810,
            ks_id=17783715,
            key="антивозрастной матирующий крем",
            result="created",
            new_bid=560,
        )

    assert "[cluster_bid_trace]" in caplog.text
    assert "step=new_bid_calculate" in caplog.text
    assert "new_bid=560" in caplog.text


@pytest.mark.parametrize(
    ("kwargs",),
    [
        ({"shop_id": "other-shop", "adv_id": 32824944},),
        ({"shop_id": "db28efff-f7a9-52f8-8342-f1a58f7d8ed3", "adv_id": 1},),
        (
            {
                "shop_id": "db28efff-f7a9-52f8-8342-f1a58f7d8ed3",
                "adv_id": 32824944,
                "nmid": 999,
            },
        ),
        (
            {
                "shop_id": "db28efff-f7a9-52f8-8342-f1a58f7d8ed3",
                "adv_id": 32824944,
                "search_adv_id": 29734515,
                "nmid": 10749810,
                "key": "другой ключ",
            },
        ),
    ],
)
def test_mismatch_does_not_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    kwargs: dict[str, object],
) -> None:
    _set_trace_env(monkeypatch)

    assert is_trace_cell(**kwargs) is False

    with caplog.at_level(logging.INFO):
        log_cluster_bid_trace(step="map_cell", **kwargs)

    assert "[cluster_bid_trace]" not in caplog.text


def test_error_detail_sanitizes_secrets() -> None:
    class FakeTokenError(Exception):
        pass

    exc = FakeTokenError("failed bearer=super-secret-token api_key=abc123")
    detail = format_error_detail(exc)

    assert detail is not None
    assert "super-secret-token" not in detail
    assert "abc123" not in detail
    assert "<redacted>" in detail


def test_sensitive_field_redacted_in_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _set_trace_env(monkeypatch)

    with caplog.at_level(logging.INFO):
        log_cluster_bid_trace(
            step="apply_after",
            shop_id="db28efff-f7a9-52f8-8342-f1a58f7d8ed3",
            adv_id=32824944,
            search_adv_id=29734515,
            nmid=10749810,
            ks_id=17783715,
            key="антивозрастной матирующий крем",
            api_token="must-not-appear",
        )

    assert "[cluster_bid_trace]" in caplog.text
    assert "must-not-appear" not in caplog.text
    assert "api_token=<redacted>" in caplog.text
