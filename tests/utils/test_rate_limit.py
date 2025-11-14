import asyncio

import pytest

from app.utils.rate_limit import rate_limited_request, _get_lock  # noqa: WPS450 - testing internals  # pyright: ignore


class DummyManager:
    def __init__(self):
        self.blocked = False
        self.ttl = 0.0
        self.errors = 0
        self.success = 0

    async def is_ip_blocked(self, ip: str):
        # simulate TTL countdown of 50 ms per check
        if self.blocked and self.ttl > 0:
            self.ttl -= 0.05
            if self.ttl <= 0:
                self.blocked = False
                self.ttl = 0.0
        return self.blocked, self.ttl

    async def block_ip(self, ip: str, ttl: float):
        self.blocked, self.ttl = True, ttl

    async def delete_block(self, ip: str):
        self.blocked = False
        self.ttl = 0.0

    async def refresh_block(self, ip: str, ttl: float):
        self.ttl = ttl

    async def increment_error_counter(self, ip: str):
        self.errors += 1
        return self.errors

    async def increment_success_counter(self, ip: str):
        self.success += 1
        return self.success

    async def set_last_error_ts(self, ip: str):
        pass

    async def get_last_error_ts(self, ip: str):
        return 0.0


@pytest.mark.asyncio
async def test_rate_limit_single_underlying_call(monkeypatch: pytest.MonkeyPatch):
    manager = DummyManager()
    calls: list[int] = []

    async def stub_get_public_ip():
        return "127.0.0.1"

    monkeypatch.setattr("app.utils.rate_limit.get_public_ip", stub_get_public_ip)

    # Use small values for testing to avoid long delays
    @rate_limited_request(manager, max_retries=3, delay=0.01)
    async def underlying(x):  # noqa: WPS430
        calls.append(x)
        await asyncio.sleep(0.01)
        if x == 0:
            # emulate TooManyRequests on first call
            from app.modules.wb_keywords_parser.wb_parser.excs import TooManyRequestsInParserError

            raise TooManyRequestsInParserError("test")
        return x

    async def runner(arg):
        try:
            return await underlying(arg)
        except Exception:  # noqa: BLE001
            return None

    await asyncio.gather(*(runner(i) for i in range(3)))

    # underlying(0) will be called 3 times (max_retries=3) before failing
    # underlying(1) will be called 1 time and succeed
    # underlying(2) will be called 1 time and succeed
    # Total: 3 + 1 + 1 = 5 calls
    assert len(calls) == 5, f"Expected 5 calls, got {len(calls)}: {calls}"
    assert calls.count(0) == 3, "underlying(0) should be called 3 times (retries)"
    assert calls.count(1) == 1, "underlying(1) should be called once"
    assert calls.count(2) == 1, "underlying(2) should be called once"

    # After error first ip should be blocked
    assert manager.blocked is True
    assert manager.errors >= 1


