"""DryRunReceiptV1 — server-issued reviewed preview evidence."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.wb_sky_control_plane.apply.enums import DryRunReceiptLifecycleState
from app.modules.wb_sky_control_plane.models.changeset import LogicalScopeV1
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus

_IMMUTABLE = ConfigDict(frozen=True, extra="forbid")


def _empty_state_tokens() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
    return {}


class DryRunReceiptBindingV1(BaseModel):
    """Immutable issue-time fields (persisted columns in Slice B)."""

    model_config = _IMMUTABLE

    receipt_id: str
    issued_at: datetime
    expires_at: datetime
    scope: LogicalScopeV1
    changeset_id: str
    semantic_digest: str
    preview_digest: str
    state_tokens: dict[str, str] = Field(default_factory=_empty_state_tokens)
    capability_projection_digest: str
    dry_run_status: DryRunStatus


class DryRunReceiptV1(BaseModel):
    """Receipt row: frozen binding + mutable lifecycle_state only."""

    model_config = ConfigDict(frozen=False, extra="forbid")

    binding: DryRunReceiptBindingV1
    lifecycle_state: DryRunReceiptLifecycleState

    @property
    def receipt_id(self) -> str:
        return self.binding.receipt_id

    @property
    def expires_at(self) -> datetime:
        return self.binding.expires_at

    def is_terminal(self) -> bool:
        """Terminal receipt states cannot authorize new apply."""
        return self.lifecycle_state in {
            DryRunReceiptLifecycleState.CONSUMED,
            DryRunReceiptLifecycleState.EXPIRED,
            DryRunReceiptLifecycleState.INVALIDATED,
            DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION,
        }

    def is_usable_for_apply(self, *, now: datetime) -> bool:
        """ISSUED/CLAIMED and not past expires_at."""
        if self.is_terminal():
            return False
        if now >= self.binding.expires_at:
            return False
        return self.lifecycle_state in {
            DryRunReceiptLifecycleState.ISSUED,
            DryRunReceiptLifecycleState.CLAIMED,
        }
