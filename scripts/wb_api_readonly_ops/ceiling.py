"""Верхний finite budget на весь Job (anti-hang), поверх stack retries."""

from __future__ import annotations

import time


class CeilingExhausted(RuntimeError):
    """Исчерпан run ceiling (время или число вызовов)."""


class RunCeiling:
    """Счётчик вызовов + deadline для orchestrator."""

    def __init__(self, *, max_seconds: float, max_calls: int) -> None:
        """Args: max_seconds — wall clock; max_calls — число family API calls."""
        if max_seconds <= 0:
            raise ValueError("max_seconds must be positive")
        if max_calls <= 0:
            raise ValueError("max_calls must be positive")
        self.max_seconds = float(max_seconds)
        self.max_calls = int(max_calls)
        self._deadline = time.monotonic() + self.max_seconds
        self.calls_used = 0
        self.exhausted = False

    def check(self) -> None:
        """Поднять CeilingExhausted если бюджет кончился."""
        if self.exhausted:
            raise CeilingExhausted("run ceiling already exhausted")
        if time.monotonic() >= self._deadline:
            self.exhausted = True
            raise CeilingExhausted("run ceiling: time budget exhausted")
        if self.calls_used >= self.max_calls:
            self.exhausted = True
            raise CeilingExhausted("run ceiling: call budget exhausted")

    def consume(self) -> None:
        """Зафиксировать один family call после check()."""
        self.check()
        self.calls_used += 1
