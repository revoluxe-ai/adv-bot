import asyncio
from typing import TypedDict


class ApiCallState(TypedDict):
    _last_query_time: float | None
    _current_pause: float
    _attempts: int
    _pool_timeout_attempts: int
    _lock: asyncio.Lock


class RequestLimitManager:
    def __init__(self):
        self.api_call_state: dict[str, ApiCallState] = {}
