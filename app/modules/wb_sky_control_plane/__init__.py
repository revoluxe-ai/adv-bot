"""WB Sky Control Plane Kernel (Change A1): read-only dry-run pipeline.

Transport-independent модели ChangeSetV1 → resolve → snapshot → classify →
capabilities → validate → state_token → semantic diff → Plan → DryRunResult.

Apply, lifecycle execution и production write-path в A1 не входят.
"""

from __future__ import annotations

from typing import Any

__all__ = ["dry_run"]


def __getattr__(name: str) -> Any:
    """Lazy import dry_run so apply subpackage imports stay lightweight."""
    if name == "dry_run":
        from app.modules.wb_sky_control_plane.kernel.pipeline import dry_run

        return dry_run
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
