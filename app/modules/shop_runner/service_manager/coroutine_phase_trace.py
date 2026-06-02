"""Точечные тайминги фаз корутин shop_runner (диагностика латентности).

Включается env ``COROUTINE_PHASE_TRACE_ADV_IDS`` — список ``adv_id`` через запятую
(например ``32824944``). Для выбранных РК пишутся INFO-логи ``[coroutine_timing]``
с ``shop_id``, ``adv_id``, именем корутины, фазы и ``duration_ms``.

Не меняет бизнес-логику; только наблюдаемость.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)

_TRACE_ADV_IDS: set[int] | None = None


def _load_trace_adv_ids() -> set[int]:
    raw = os.environ.get("COROUTINE_PHASE_TRACE_ADV_IDS", "").strip()
    if not raw:
        return set()
    result: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            result.add(int(part))
    return result


def is_trace_adv(adv_id: int) -> bool:
    """True, если для ``adv_id`` включён пошаговый тайминг."""
    global _TRACE_ADV_IDS
    if _TRACE_ADV_IDS is None:
        _TRACE_ADV_IDS = _load_trace_adv_ids()
    if not _TRACE_ADV_IDS:
        return False
    return adv_id in _TRACE_ADV_IDS


def batch_has_trace_adv(adv_ids: Iterable[int]) -> bool:
    """True, если в пакете есть хотя бы одна РК из whitelist тайминга."""
    return any(is_trace_adv(aid) for aid in adv_ids)


def log_coroutine_phase(
    *,
    coroutine: str,
    phase: str,
    step: str,
    shop_id: str,
    adv_id: int | None = None,
    duration_ms: float | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Структурированный лог одной точки тайминга."""
    parts: list[str] = [
        "[coroutine_timing]",
        f"coroutine={coroutine}",
        f"phase={phase}",
        f"step={step}",
        f"shop_id={shop_id}",
    ]
    if adv_id is not None:
        parts.append(f"adv_id={adv_id}")
    if duration_ms is not None:
        parts.append(f"duration_ms={duration_ms:.2f}")
    if extra:
        for key, value in extra.items():
            parts.append(f"{key}={value}")
    logger.info(" ".join(parts))


class AdvPhaseTrace:
    """Тайминг фаз одной РК (``process_adv_v3`` и per-adv шаги bidder)."""

    def __init__(self, *, coroutine: str, shop_id: str, adv_id: int) -> None:
        self.coroutine = coroutine
        self.shop_id = shop_id
        self.adv_id = adv_id
        self.enabled = is_trace_adv(adv_id)

    @classmethod
    def for_complex_adv(cls, *, coroutine: str, adv: Any) -> AdvPhaseTrace:
        """Собрать trace из ``ComplexAdv`` (``shop_id``, ``adv_id``)."""
        return cls(coroutine=coroutine, shop_id=adv.shop_id, adv_id=adv.adv_id)

    def marker(self, phase: str, extra: dict[str, object] | None = None) -> None:
        """Точка без длительности (счётчики, размеры коллекций)."""
        if not self.enabled:
            return
        log_coroutine_phase(
            coroutine=self.coroutine,
            phase=phase,
            step="marker",
            shop_id=self.shop_id,
            adv_id=self.adv_id,
            extra=cast_extra(extra),
        )

    def dbg_phase(self, name: str, extra: dict[str, object] | None = None) -> None:
        """Колбэк для подфаз ``_load_v3_wb_context`` (step=marker, без длительности)."""
        if not self.enabled:
            return
        log_coroutine_phase(
            coroutine=self.coroutine,
            phase=name,
            step="marker",
            shop_id=self.shop_id,
            adv_id=self.adv_id,
            extra=cast_extra(extra),
        )

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        if not self.enabled:
            yield
            return
        log_coroutine_phase(
            coroutine=self.coroutine,
            phase=name,
            step="start",
            shop_id=self.shop_id,
            adv_id=self.adv_id,
        )
        started = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - started) * 1000.0
            log_coroutine_phase(
                coroutine=self.coroutine,
                phase=name,
                step="end",
                shop_id=self.shop_id,
                adv_id=self.adv_id,
                duration_ms=duration_ms,
            )


class ShopBatchPhaseTrace:
    """Тайминг фаз корутины на уровне магазина (пакет РК)."""

    def __init__(
        self,
        *,
        coroutine: str,
        shop_id: str,
        adv_ids: Iterable[int],
    ) -> None:
        self.coroutine = coroutine
        self.shop_id = shop_id
        self.enabled = batch_has_trace_adv(adv_ids)
        self._traced_adv_ids = [aid for aid in adv_ids if is_trace_adv(aid)]

    @classmethod
    def from_complex_advs(cls, *, coroutine: str, advs: Iterable[Any]) -> ShopBatchPhaseTrace:
        """Собрать batch-trace из списка ``ComplexAdv``."""
        adv_list = list(advs)
        shop_id = adv_list[0].shop_id if adv_list else "unknown"
        return cls(
            coroutine=coroutine,
            shop_id=shop_id,
            adv_ids=[a.adv_id for a in adv_list],
        )

    def marker(
        self,
        phase: str,
        *,
        adv_id: int | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        """Точка без длительности на уровне магазина или одной РК."""
        if not self.enabled:
            return
        merged: dict[str, Any] | None = cast_extra(extra)
        if adv_id is None and self._traced_adv_ids:
            base = {"traced_adv_ids": self._traced_adv_ids}
            merged = {**base, **(merged or {})}
        log_coroutine_phase(
            coroutine=self.coroutine,
            phase=phase,
            step="marker",
            shop_id=self.shop_id,
            adv_id=adv_id,
            extra=merged,
        )

    @contextmanager
    def phase(self, name: str, *, adv_id: int | None = None) -> Iterator[None]:
        if not self.enabled:
            yield
            return
        log_adv_id = adv_id
        log_coroutine_phase(
            coroutine=self.coroutine,
            phase=name,
            step="start",
            shop_id=self.shop_id,
            adv_id=log_adv_id,
            extra={"traced_adv_ids": self._traced_adv_ids} if log_adv_id is None else None,
        )
        started = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - started) * 1000.0
            log_coroutine_phase(
                coroutine=self.coroutine,
                phase=name,
                step="end",
                shop_id=self.shop_id,
                adv_id=log_adv_id,
                duration_ms=duration_ms,
                extra={"traced_adv_ids": self._traced_adv_ids} if log_adv_id is None else None,
            )


def cast_extra(extra: dict[str, object] | None) -> dict[str, Any] | None:
    if extra is None:
        return None
    return {str(k): v for k, v in extra.items()}
