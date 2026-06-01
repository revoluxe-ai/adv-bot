"""NDJSON-пробы для Cursor debug session (только диагностика).

Файл лога: ``debug-95574f.log`` в корне репозитория.
Анализ незавершённых шагов: ``find_unclosed_steps(path)`` — start без end/error.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

SESSION_ID = "95574f"
_LOG_PATH = Path(__file__).resolve().parents[2] / "debug-95574f.log"

_tick_id: ContextVar[str | None] = ContextVar("debug_tick_id", default=None)
_shop_id: ContextVar[str | None] = ContextVar("debug_shop_id", default=None)

FOCUS_ADV_ID = 32824944
FOCUS_NMID = 10749810
FOCUS_SHOP_ID = "db28efff-f7a9-52f8-8342-f1a58f7d8ed3"


def _write(payload: dict[str, Any]) -> None:
    tick = _tick_id.get()
    shop = _shop_id.get()
    if tick is not None:
        payload.setdefault("tickId", tick)
    if shop is not None:
        payload.setdefault("shopId", shop)
    payload.setdefault("sessionId", SESSION_ID)
    payload.setdefault("timestamp", int(time.time() * 1000))
    try:
        with _LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def begin_tick(*, shop_id: str, run_id: str = "pre-fix") -> str:
    """Новый tick корутины; возвращает ``tick_id`` для корреляции строк лога."""
    tick_id = uuid.uuid4().hex[:12]
    _tick_id.set(tick_id)
    _shop_id.set(shop_id)
    # #region agent log
    _write(
        {
            "location": "debug_session_probe.py:begin_tick",
            "message": "tick.begin",
            "hypothesisId": "H8",
            "runId": run_id,
            "data": {
                "step": "start",
                "step_id": f"{tick_id}::tick",
                "shop_id": shop_id,
                "coroutine": "update_cluster_bids",
                "decorator_timeout_sec": 900,
                "decorator_pause_on_success_sec": 300,
                "coroutine_inflight_guard": "none_for_update_cluster_bids",
            },
        }
    )
    probe_proxy_env(hypothesis_id="H5")
    probe_tasks_manager_state(hypothesis_id="H3")
    # #endregion
    return tick_id


def end_tick(*, outcome: str, run_id: str = "pre-fix", **data: Any) -> None:
    """``outcome``: ``success`` | ``skipped`` | ``error`` | ``timeout``."""
    tick = _tick_id.get() or "unknown"
    # #region agent log
    _write(
        {
            "location": "debug_session_probe.py:end_tick",
            "message": "tick.end",
            "hypothesisId": "H8",
            "runId": run_id,
            "data": {
                "step": "end",
                "step_id": f"{tick}::tick",
                "outcome": outcome,
                **data,
            },
        }
    )
    # #endregion


def get_tick_id() -> str:
    return _tick_id.get() or "no-tick"


def probe_event(
    location: str,
    message: str,
    *,
    hypothesis_id: str,
    run_id: str = "pre-fix",
    step: str | None = None,
    step_id: str | None = None,
    **data: Any,
) -> None:
    payload_data: dict[str, Any] = dict(data)
    if step is not None:
        payload_data["step"] = step
    if step_id is not None:
        payload_data["step_id"] = step_id
    # #region agent log
    _write(
        {
            "location": location,
            "message": message,
            "hypothesisId": hypothesis_id,
            "runId": run_id,
            "data": payload_data,
        }
    )
    # #endregion


def probe_step_start(
    step_id: str,
    *,
    location: str,
    message: str,
    hypothesis_id: str,
    run_id: str = "pre-fix",
    **data: Any,
) -> None:
    probe_event(
        location,
        message,
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        step="start",
        step_id=step_id,
        **data,
    )


def probe_step_end(
    step_id: str,
    *,
    location: str,
    message: str,
    hypothesis_id: str,
    run_id: str = "pre-fix",
    duration_ms: float | None = None,
    **data: Any,
) -> None:
    payload: dict[str, Any] = dict(data)
    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 2)
    probe_event(
        location,
        message,
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        step="end",
        step_id=step_id,
        **payload,
    )


def probe_step_error(
    step_id: str,
    exc: BaseException,
    *,
    location: str,
    message: str,
    hypothesis_id: str,
    run_id: str = "pre-fix",
    duration_ms: float | None = None,
    **data: Any,
) -> None:
    payload: dict[str, Any] = {
        "exc_type": type(exc).__name__,
        "exc_msg": str(exc)[:500],
        **data,
    }
    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 2)
    if isinstance(exc, asyncio.CancelledError):
        payload["cancelled"] = True
    probe_event(
        location,
        message,
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        step="error",
        step_id=step_id,
        **payload,
    )


def probe_step_stuck(
    step_id: str,
    *,
    location: str,
    message: str,
    hypothesis_id: str,
    reason: str,
    run_id: str = "pre-fix",
    **data: Any,
) -> None:
    """Явный маркер зависания (timeout tick, grace cancel и т.д.)."""
    probe_event(
        location,
        message,
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        step="stuck",
        step_id=step_id,
        reason=reason,
        **data,
    )


@asynccontextmanager
async def probe_span(
    location: str,
    message: str,
    *,
    hypothesis_id: str,
    run_id: str = "pre-fix",
    step_id: str | None = None,
    **data: Any,
) -> AsyncIterator[dict[str, Any]]:
    """start → yield extra → end или error."""
    sid = step_id or f"{get_tick_id()}::{location}::{message}"
    t0 = time.perf_counter()
    extra: dict[str, Any] = {}
    probe_step_start(
        sid,
        location=location,
        message=message,
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        **data,
    )
    try:
        yield extra
    except BaseException as exc:
        ms = (time.perf_counter() - t0) * 1000
        probe_step_error(
            sid,
            exc,
            location=location,
            message=message,
            hypothesis_id=hypothesis_id,
            run_id=run_id,
            duration_ms=ms,
            **data,
            **extra,
        )
        raise
    else:
        ms = (time.perf_counter() - t0) * 1000
        probe_step_end(
            sid,
            location=location,
            message=message,
            hypothesis_id=hypothesis_id,
            run_id=run_id,
            duration_ms=ms,
            **data,
            **extra,
        )


def probe_duration_ms() -> float:
    return time.perf_counter()


def probe_proxy_env(*, hypothesis_id: str = "H5") -> None:
    keys = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
    )
    present = {k: bool(os.environ.get(k)) for k in keys}
    probe_event(
        "debug_session_probe.py:probe_proxy_env",
        "runtime.proxy_env",
        hypothesis_id=hypothesis_id,
        step="info",
        proxy_keys_present=present,
    )


def probe_tasks_manager_state(*, hypothesis_id: str = "H3") -> None:
    probe_event(
        "debug_session_probe.py:probe_tasks_manager_state",
        "runtime.tasks_manager",
        hypothesis_id=hypothesis_id,
        step="info",
        handler_timeout_sec="see TasksManager.DEFAULT_TASK_HANDLER_TIMEOUT_SECONDS",
        note="None means handler can hang without TasksManager timeout",
    )


def probe_db_session_hint(
    *,
    phase: str,
    hypothesis_id: str = "H4",
) -> None:
    """Эвристика: PG session не должен жить через внешний I/O (scoped ``async with sm()``)."""
    probe_event(
        "debug_session_probe.py:probe_db_session_hint",
        "runtime.db_session_hint",
        hypothesis_id=hypothesis_id,
        step="info",
        phase=phase,
        expected="no_open_pg_session_outside_async_with_sm",
    )


def probe_focus_advs(
    advs: Any,
    *,
    shop_id: str,
    hypothesis_id: str = "H11",
) -> None:
    """Срез по проблемному adv/nmid/shop."""
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
        ComplexAdv,
    )

    if not isinstance(advs, list):
        return
    typed: list[ComplexAdv] = advs
    focus_adv = [a for a in typed if a.adv_id == FOCUS_ADV_ID]
    focus_auction = [
        a
        for a in typed
        if a.auction_adv_id == FOCUS_ADV_ID or a.search_adv_id == FOCUS_ADV_ID
    ]
    focus_nmid = [a for a in typed if FOCUS_NMID in a.nmids]
    probe_event(
        "debug_session_probe.py:probe_focus_advs",
        "focus.adv_contour",
        hypothesis_id=hypothesis_id,
        step="info",
        shop_id_match=shop_id == FOCUS_SHOP_ID,
        batch_size=len(typed),
        focus_adv_id_in_batch=len(focus_adv) > 0,
        focus_auction_or_search_id_in_batch=len(focus_auction) > 0,
        focus_nmid_in_batch=len(focus_nmid) > 0,
        focus_adv_bot_bidder_active=(
            focus_adv[0].bot_active and focus_adv[0].bidder_active if focus_adv else None
        ),
    )


def probe_keyword_pg_insert(
    *,
    adv_id: int,
    original_adv_id: int,
    source: str,
    texts_in: int,
    new_texts_count: int,
    hypothesis_id: str = "H12",
    run_id: str = "keywords-v1",
) -> None:
    """PG INSERT новых ``KeywordSetting`` (не WB API)."""
    # #region agent log
    probe_event(
        "keywords_manager.py:_add_new_keyword_settings_to_session",
        "keyword.new_texts_pg",
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        step="info",
        adv_id=adv_id,
        original_adv_id=original_adv_id,
        source=source,
        texts_in=texts_in,
        new_texts_count=new_texts_count,
        focus_adv=adv_id == FOCUS_ADV_ID,
    )
    # #endregion


def probe_keyword_ch_stats(
    *,
    adv_id: int,
    stats_count: int,
    min_days: int,
    min_views: int,
    hypothesis_id: str = "H12",
    run_id: str = "keywords-v1",
) -> None:
    """Сколько кластеров/ключей вернул CH до PG insert."""
    # #region agent log
    probe_event(
        "calculated_keywords_manager.py:get_calculated_keywords",
        "keyword.ch_stats_loaded",
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        step="info",
        adv_id=adv_id,
        stats_count=stats_count,
        min_days=min_days,
        min_views=min_views,
        focus_adv=adv_id == FOCUS_ADV_ID,
    )
    # #endregion


def probe_v3_adv_result(
    *,
    adv_id: int,
    keywords_loaded: int,
    campaign_mode: str,
    early_return: str | None = None,
    preamble_bootstrap: int = 0,
    preamble_expansion: int = 0,
    selector_up: int = 0,
    selector_down: int = 0,
    selector_force_off: int = 0,
    flushed: bool = False,
    hypothesis_id: str = "H13",
    run_id: str = "keywords-v1",
) -> None:
    """Итог одного ``process_adv_v3`` (actions / flush, не создание текстов)."""
    # #region agent log
    probe_event(
        "orchestrator.py:process_adv_v3",
        "v3.adv_tick_result",
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        step="info",
        adv_id=adv_id,
        keywords_loaded=keywords_loaded,
        campaign_mode=campaign_mode,
        early_return=early_return,
        preamble_bootstrap=preamble_bootstrap,
        preamble_expansion=preamble_expansion,
        selector_up=selector_up,
        selector_down=selector_down,
        selector_force_off=selector_force_off,
        flushed=flushed,
        focus_adv=adv_id == FOCUS_ADV_ID,
    )
    # #endregion


def probe_freshness_guard_decision(
    *,
    shop_id: str,
    adv_id: int,
    operation_name: str,
    cache_key: str,
    cache_kind: str,
    decision: str,
    is_fresh: bool | None = None,
    is_stale_over_6h: bool | None = None,
    reason: str | None = None,
    cache_updated_at: str | None = None,
    stale_threshold_hours: float = 1.0,
    emergency_threshold_hours: float = 6.0,
    hypothesis_id: str = "H15",
    run_id: str = "freshness-v1",
) -> None:
    """Решение stats_freshness guard для одного adv (см. ``_split_advs_by_stats_freshness``)."""
    # #region agent log
    probe_event(
        "manager.py:_split_advs_by_stats_freshness",
        "freshness.guard_decision",
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        step="info",
        shop_id=shop_id,
        adv_id=adv_id,
        op=operation_name,
        cache_key=cache_key,
        cache_kind=cache_kind,
        decision=decision,
        is_fresh=is_fresh,
        is_stale_over_6h=is_stale_over_6h,
        reason=reason,
        cache_updated_at=cache_updated_at,
        stale_threshold_hours=stale_threshold_hours,
        emergency_threshold_hours=emergency_threshold_hours,
        focus_adv=adv_id == FOCUS_ADV_ID,
    )
    # #endregion


def probe_shop_coroutine(
    coroutine: str,
    phase: str,
    *,
    shop_id: str,
    hypothesis_id: str = "H14",
    run_id: str = "keywords-v1",
    **data: Any,
) -> None:
    """Тик shop-корутин (V3 batch, clusters today, inflight skip)."""
    # #region agent log
    probe_event(
        "manager.py",
        f"coroutine.{coroutine}.{phase}",
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        step="info",
        shop_id=shop_id,
        coroutine=coroutine,
        phase=phase,
        **data,
    )
    # #endregion


def probe_timestamp_gate(
    *,
    phase: str,
    hypothesis_id: str = "H10",
    **data: Any,
) -> None:
    probe_event(
        "update_cluster_bids_manager.py:timestamp_gate",
        f"timestamp.{phase}",
        hypothesis_id=hypothesis_id,
        step="info",
        note="redis last_cluster_bids_update only after successful apply_command",
        **data,
    )


def probe_run_tasks_results(
    step_id: str,
    results: list[Any],
    branch_names: list[str],
    *,
    location: str,
    hypothesis_id: str,
    return_exceptions: bool,
) -> None:
    """После ``run_tasks``: cancelled / exception / ok по каждой ветке."""
    for name, res in zip(branch_names, results, strict=False):
        branch_step = f"{step_id}::{name}"
        if isinstance(res, BaseException):
            probe_step_error(
                branch_step,
                res,
                location=location,
                message=f"run_tasks.branch.{name}",
                hypothesis_id=hypothesis_id,
                return_exceptions=return_exceptions,
                branch=name,
            )
        else:
            probe_step_end(
                branch_step,
                location=location,
                message=f"run_tasks.branch.{name}",
                hypothesis_id=hypothesis_id,
                branch=name,
                result_type=type(res).__name__,
            )


def find_unclosed_steps(log_path: Path | None = None) -> list[dict[str, Any]]:
    """Возвращает step_id с ``start`` без ``end``/``error``/``stuck`` (для отчёта)."""
    path = log_path or _LOG_PATH
    if not path.is_file():
        return []
    opened: dict[str, dict[str, Any]] = {}
    closed: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        data = row.get("data") or {}
        sid = data.get("step_id")
        if not sid:
            continue
        step = data.get("step")
        if step == "start":
            opened[sid] = row
        elif step in ("end", "error", "stuck"):
            closed.add(sid)
    unclosed = [
        {"step_id": sid, "started": opened[sid]}
        for sid in opened
        if sid not in closed
    ]
    return unclosed


async def probe_branch(
    branch: str,
    coro: Any,
    *,
    location: str,
    hypothesis_id: str,
    **data: Any,
) -> Any:
    """Обёртка одной параллельной ветки _get_bidder_update_data."""
    sid = f"{get_tick_id()}::bidder_parallel::{branch}"
    t0 = probe_duration_ms()
    probe_step_start(
        sid,
        location=location,
        message=f"branch.{branch}",
        hypothesis_id=hypothesis_id,
        branch=branch,
        **data,
    )
    try:
        result = await coro
    except BaseException as exc:
        probe_step_error(
            sid,
            exc,
            location=location,
            message=f"branch.{branch}",
            hypothesis_id=hypothesis_id,
            duration_ms=(probe_duration_ms() - t0) * 1000,
            branch=branch,
            **data,
        )
        raise
    else:
        probe_step_end(
            sid,
            location=location,
            message=f"branch.{branch}",
            hypothesis_id=hypothesis_id,
            duration_ms=(probe_duration_ms() - t0) * 1000,
            branch=branch,
            **data,
        )
        return result
