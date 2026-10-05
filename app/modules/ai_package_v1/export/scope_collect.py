"""Сбор adv_id и main_nmid из PG scope DTO."""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.ai_package_v1.scope.dto import ExportScopeAdv


def collect_scoped_adv_ids(scope: Sequence[ExportScopeAdv]) -> list[int]:
    """Уникальные adv_id (auto и search раздельно, без слияния)."""
    ids: set[int] = set()
    for row in scope:
        ids.add(row.auto_adv_id)
        if row.search_adv_id is not None:
            ids.add(row.search_adv_id)
    return sorted(ids)


def collect_main_nmids(scope: Sequence[ExportScopeAdv]) -> list[int]:
    """Уникальные main_nmid из inventory (``None`` пропускаются)."""
    return sorted({row.main_nmid for row in scope if row.main_nmid is not None})
