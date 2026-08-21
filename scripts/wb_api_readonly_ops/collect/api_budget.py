"""Internal API call budget для collect pagination (отдельно от family ceiling)."""

from __future__ import annotations

import time


class ApiBudgetExhausted(RuntimeError):
    """Исчерпан collect API budget."""


class ApiCallBudget:
    """Wall-clock + max API calls для full collect runner."""

    def __init__(self, *, max_seconds: float, max_api_calls: int) -> None:
        if max_seconds <= 0:
            raise ValueError("max_seconds must be positive")
        if max_api_calls <= 0:
            raise ValueError("max_api_calls must be positive")
        self.max_seconds = float(max_seconds)
        self.max_api_calls = int(max_api_calls)
        self._deadline = time.monotonic() + self.max_seconds
        self.api_calls_used = 0
        self.exhausted = False

    def check(self) -> None:
        if self.exhausted:
            raise ApiBudgetExhausted("collect API budget already exhausted")
        if time.monotonic() >= self._deadline:
            self.exhausted = True
            raise ApiBudgetExhausted("collect API budget: time exhausted")
        if self.api_calls_used >= self.max_api_calls:
            self.exhausted = True
            raise ApiBudgetExhausted("collect API budget: call count exhausted")

    def consume(self, count: int = 1) -> None:
        self.check()
        self.api_calls_used += count
