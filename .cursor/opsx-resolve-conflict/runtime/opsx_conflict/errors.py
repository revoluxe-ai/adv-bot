"""Ошибки sealed runtime /opsx-resolve-conflict.

CLI StopRequired envelope constants (R29) live here so boot/runtime share one
schema without depending on orchestrator internals.
"""

from __future__ import annotations

from typing import Any, Mapping

CLI_STOP_ENVELOPE_SCHEMA = "opsx-resolve-conflict/cli-stop-envelope/v1"
CLI_STOP_SCHEMA_VERSION = "1"
CLI_STOP_EXIT_CODE = 78

# Stable reason → gate mapping for typed STOP envelopes (exact replay assertions).
STOP_REASON_REACHED_GATE: Mapping[str, str] = {
    "PACKAGE_GO_CAPABILITY_DISABLED": "package_compatibility_gate",
    "SCOPE_FILE_REQUIRED": "cli_argument_gate",
    "EXTERNAL_TRUST_ROOT_MISSING": "package_compatibility_gate",
    "EXTERNAL_TRUST_ROOT_MISMATCH": "package_compatibility_gate",
    "PACKAGE_HASH_MISMATCH": "package_compatibility_gate",
}


class PolicyViolation(RuntimeError):
    """Нарушение typed policy (запрещённый argv / API)."""

    def __init__(self, reason: str, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.details = dict(details or {})


class StateDrift(RuntimeError):
    """Fingerprint или scope изменились между шагами."""


class StopRequired(RuntimeError):
    """Нормативный STOP_FOR_OWNER / fail-closed halt."""

    def __init__(self, reason: str, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.details = dict(details or {})
