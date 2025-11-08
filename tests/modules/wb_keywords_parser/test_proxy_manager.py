from __future__ import annotations

import pytest

from app.modules.wb_keywords_parser.wb_parser.proxy_manager import (
    ParserProxy,
    ProxyProxyManager,
)


class _FakeTime:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def time(self) -> float:
        return self.value


def test_report_success_and_failure_counters() -> None:
    proxy = ParserProxy(name="proxy-1", rate_limit_key="proxy-1")
    manager = ProxyProxyManager([proxy])

    manager.report_failure(proxy)
    manager.report_failure(proxy)
    assert proxy.consecutive_failures == 2
    assert proxy.consecutive_successes == 0

    manager.report_success(proxy)
    assert proxy.consecutive_failures == 0
    assert proxy.consecutive_successes == 1


def test_report_rate_limit_sets_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    proxy = ParserProxy(name="proxy-1", rate_limit_key="proxy-1")
    manager = ProxyProxyManager([proxy])

    fake_time = _FakeTime(100.0)
    monkeypatch.setattr(
        "app.modules.wb_keywords_parser.wb_parser.proxy_manager.time",
        fake_time,
    )

    manager.report_rate_limit(proxy, 5.0)
    assert proxy.cooldown_until == pytest.approx(105.0)
    assert proxy.in_cooldown() is True

    fake_time.value = 110.0
    assert proxy.in_cooldown() is False


def test_acquire_proxy_skips_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_time = _FakeTime(100.0)
    monkeypatch.setattr(
        "app.modules.wb_keywords_parser.wb_parser.proxy_manager.time",
        fake_time,
    )

    proxy_1 = ParserProxy(name="proxy-1", rate_limit_key="proxy-1", cooldown_until=150.0)
    proxy_2 = ParserProxy(name="proxy-2", rate_limit_key="proxy-2", cooldown_until=0.0)
    manager = ProxyProxyManager([proxy_1, proxy_2])

    chosen = manager.acquire_proxy()
    assert chosen is proxy_2

    proxy_2.cooldown_until = 140.0
    chosen = manager.acquire_proxy()
    assert chosen is proxy_2
