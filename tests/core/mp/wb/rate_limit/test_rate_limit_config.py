from dataclasses import dataclass

import pytest

from app.core.mp.wb.adapters.base_adapter import WBBaseAdapter
from app.core.mp.wb.decorators.rate_limit import rate_limit_decorator
from app.core.mp.wb.rate_limit.storage import RateLimitConfig
from app.core.mp.wb.rate_limit.storage import RateLimitStorage


@dataclass
class _DummyResponse:
    status_code: int = 200
    headers: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.headers is None:
            self.headers = {}


@pytest.fixture(autouse=True)
def _reset_rate_limit_cache() -> None:
    WBBaseAdapter._rate_limit_storage_cache.clear()


class _BaseTestAdapter(WBBaseAdapter):
    section = "test"
    version = "v1"

    def __init__(self) -> None:
        super().__init__("shop-1")


@pytest.mark.asyncio
async def test_rate_limit_uses_section_defaults() -> None:
    class Adapter(_BaseTestAdapter):
        section_rate_limit = RateLimitConfig(requests_per_interval=5, interval_seconds=1.0)

        @rate_limit_decorator
        async def call(self) -> _DummyResponse:
            return _DummyResponse()

    adapter = Adapter()
    await adapter.call()
    record = adapter.rate_limit_storage.get("shop-1", "test", "call")
    assert record.config == Adapter.section_rate_limit


@pytest.mark.asyncio
async def test_rate_limit_override_from_decorator_args() -> None:
    override = RateLimitConfig(requests_per_interval=2, interval_seconds=10.0, burst=3)

    class Adapter(_BaseTestAdapter):
        section_rate_limit = RateLimitConfig(requests_per_interval=1, interval_seconds=60.0)

        @rate_limit_decorator(
            requests_per_interval=override.requests_per_interval,
            interval_seconds=override.interval_seconds,
            burst=override.burst,
        )
        async def call(self) -> _DummyResponse:
            return _DummyResponse()

    adapter = Adapter()
    await adapter.call()
    record = adapter.rate_limit_storage.get("shop-1", "test", "call")
    assert record.config == override


@pytest.mark.asyncio
async def test_preflight_delay_respects_config_min_interval() -> None:
    storage = RateLimitStorage()
    config = RateLimitConfig(requests_per_interval=2, interval_seconds=1.0)
    await storage.register_config("shop", "sec", "method", config)

    first_delay = await storage.preflight_delay("shop", "sec", "method")
    second_delay = await storage.preflight_delay("shop", "sec", "method")

    assert first_delay == pytest.approx(0, abs=1e-6)
    assert second_delay > 0


@pytest.mark.asyncio
async def test_rate_limit_accepts_limits_interval_aliases() -> None:
    class Adapter(_BaseTestAdapter):
        section_rate_limit = RateLimitConfig(requests_per_interval=10, interval_seconds=5.0)

        @rate_limit_decorator(limits=3, interval=2.0)
        async def call(self) -> _DummyResponse:
            return _DummyResponse()

    adapter = Adapter()
    await adapter.call()
    record = adapter.rate_limit_storage.get("shop-1", "test", "call")
    expected = RateLimitConfig(requests_per_interval=3, interval_seconds=2.0)
    assert record.config == expected

