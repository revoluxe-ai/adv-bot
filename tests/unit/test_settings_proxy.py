"""Tests for PROXY (Telegram aiohttp session; unset means no proxy)."""

import pytest

from app.settings.settings_master import Settings


@pytest.mark.unit
def test_proxy_unset_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROXY", raising=False)
    assert Settings().PROXY is None


@pytest.mark.unit
def test_proxy_empty_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROXY", "")
    assert Settings().PROXY is None


@pytest.mark.unit
def test_proxy_whitespace_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROXY", "  \t  ")
    assert Settings().PROXY is None


@pytest.mark.unit
def test_proxy_set_value_is_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROXY", "  http://proxy.example:8080  ")
    assert Settings().PROXY == "http://proxy.example:8080"


@pytest.mark.unit
def test_v3_above_target_min_bid_enabled_default_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("V3_ABOVE_TARGET_MIN_BID_ENABLED", raising=False)
    assert Settings().V3_ABOVE_TARGET_MIN_BID_ENABLED is False


@pytest.mark.unit
def test_v3_above_target_min_bid_enabled_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("V3_ABOVE_TARGET_MIN_BID_ENABLED", "true")
    assert Settings().V3_ABOVE_TARGET_MIN_BID_ENABLED is True


@pytest.mark.unit
def test_v3_above_target_min_bid_enabled_invalid_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("V3_ABOVE_TARGET_MIN_BID_ENABLED", "maybe")
    with pytest.raises(Exception, match="V3_ABOVE_TARGET_MIN_BID_ENABLED"):
        _ = Settings().V3_ABOVE_TARGET_MIN_BID_ENABLED
