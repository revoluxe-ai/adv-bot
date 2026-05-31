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
