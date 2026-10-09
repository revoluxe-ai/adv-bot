"""Optional test-only hooks (not used in production wiring)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.modules.common_slaves.wildberries.models.models import AdvSetting
    from app.modules.wb_sky_control_plane.apply.models.evidence import ApplyEvidenceV1
    from app.modules.wb_sky_control_plane.models.plan import PlanV1


@dataclass(slots=True)
class ApplyServiceTestHooks:
    """Injectable seams for disposable-PG certification tests."""

    force_post_write_verify_fail: bool = False
    force_evidence_insert_fail: bool = False
    force_ambiguous_commit: bool = False
    post_write_verify_override: (
        Callable[
            [AsyncSession, PlanV1, dict[str, AdvSetting]],
            Awaitable[bool],
        ]
        | None
    ) = None
    evidence_insert_override: (
        Callable[[ApplyEvidenceV1], Awaitable[ApplyEvidenceV1]] | None
    ) = None
