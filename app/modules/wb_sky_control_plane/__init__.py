"""WB Sky Control Plane Kernel (Change A1): read-only dry-run pipeline.

Transport-independent модели ChangeSetV1 → resolve → snapshot → classify →
capabilities → validate → state_token → semantic diff → Plan → DryRunResult.

Apply, lifecycle execution и production write-path в A1 не входят.
"""

from app.modules.wb_sky_control_plane.kernel.pipeline import dry_run

__all__ = ["dry_run"]
