"""Compare-and-set vocabulary for ad control persistence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RevisionConflictError(Exception):
    """Expected revision does not match authoritative row (or absent slot)."""


class PersistedInheritForbiddenError(Exception):
    """INHERIT must not be stored on campaign rows."""


class UnsupportedSchemaVersionError(Exception):
    """Registry does not support requested schema_version (fail closed)."""


class AdControlMutationKind(StrEnum):
    """Transport-independent mutation intent."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DISABLE = "DISABLE"
    CLEAR_TO_INHERIT = "CLEAR_TO_INHERIT"
    NO_OP = "NO_OP"


@dataclass(frozen=True, slots=True)
class AdControlMutationResult:
    """Outcome of a successful CAS mutation (repository layer)."""

    kind: AdControlMutationKind
    revision: int | None
    state_token: str | None
