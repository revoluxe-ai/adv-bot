"""Apply Authority service-level exceptions."""

from app.modules.wb_sky_control_plane.apply.models.outcomes import ApplyOutcomeV1


class AmbiguousCommitAcknowledgementError(Exception):
    """Authoritative COMMIT outcome is unknown (connection lost after possible commit)."""


class ApplyOutcomeRollback(Exception):
    """Internal: roll back authoritative txn and return non-VERIFIED outcome."""

    def __init__(self, outcome: ApplyOutcomeV1) -> None:
        self.outcome = outcome
        super().__init__(outcome.status.value)
