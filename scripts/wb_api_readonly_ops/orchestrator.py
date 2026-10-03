"""Оркестрация preflight/collect с injectable family runners и run ceiling."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from scripts.wb_api_readonly_ops.ceiling import CeilingExhausted, RunCeiling
from scripts.wb_api_readonly_ops.models import (
    FAMILY_ORDER,
    FamilyName,
    FamilyResult,
    FamilyStatus,
    Mode,
    RunReport,
    compute_overall_status,
)

FamilyRunner = Callable[[Mode, dict[str, Any]], Awaitable[FamilyResult]]


async def run_ops(
    *,
    shop_id: str,
    mode: Mode,
    runners: dict[FamilyName, FamilyRunner],
    ceiling: RunCeiling,
    shared: dict[str, Any] | None = None,
) -> RunReport:
    """Прогнать семьи (ORDERS первым); PARTIAL при gaps; не заявлять Web PASS.

    Args:
        shop_id: кабинет (arg only).
        mode: preflight | collect.
        runners: injectable per-family async callables.
        ceiling: верхний budget на весь run.
        shared: mutable bag (например nmids из cards для analytics).
    """
    ctx: dict[str, Any] = shared if shared is not None else {}
    ctx.setdefault("shop_id", shop_id)
    results: list[FamilyResult] = []
    exhausted = False
    done: set[FamilyName] = set()

    for family in FAMILY_ORDER:
        runner = runners.get(family)
        if runner is None:
            results.append(
                FamilyResult(
                    family=family,
                    status=FamilyStatus.GAP,
                    gaps=[f"no runner mapped for family {family.value}"],
                )
            )
            done.add(family)
            continue
        try:
            ceiling.consume()
            result = await runner(mode, ctx)
            results.append(result)
            done.add(family)
        except CeilingExhausted as exc:
            exhausted = True
            results.append(
                FamilyResult(
                    family=family,
                    status=FamilyStatus.FAILED,
                    gaps=["run ceiling exhausted"],
                    error=str(exc),
                )
            )
            done.add(family)
            for rest in FAMILY_ORDER:
                if rest in done:
                    continue
                results.append(
                    FamilyResult(
                        family=rest,
                        status=FamilyStatus.GAP,
                        gaps=["skipped: run ceiling exhausted"],
                    )
                )
                done.add(rest)
            break
        except Exception as exc:  # noqa: BLE001 — best-effort collect
            results.append(
                FamilyResult(
                    family=family,
                    status=FamilyStatus.FAILED,
                    gaps=[f"{family.value} raised"],
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            done.add(family)

    return RunReport(
        mode=mode,
        shop_id=shop_id,
        overall_status=compute_overall_status(results),
        families=results,
        ceiling_max_seconds=ceiling.max_seconds,
        ceiling_max_calls=ceiling.max_calls,
        ceiling_calls_used=ceiling.calls_used,
        ceiling_exhausted=ceiling.exhausted or exhausted,
    )
