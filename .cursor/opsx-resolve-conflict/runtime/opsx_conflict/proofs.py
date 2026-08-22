"""Runtime-issued proof tokens binding RUN_ID / fingerprint / scope (RC04-C03)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .errors import PolicyViolation
from .hashutil import sha256_canonical


@dataclass(frozen=True)
class Proof:
    """Immutable proof token issued only by the sealed orchestrator."""

    kind: str
    run_id: str
    fingerprint: str
    scope_sha256: str
    payload: Mapping[str, Any]
    token: str

    @staticmethod
    def issue(
        kind: str,
        *,
        run_id: str,
        fingerprint: str,
        scope_sha256: str,
        payload: Mapping[str, Any] | None = None,
    ) -> "Proof":
        """Create a tamper-evident proof for a transition."""
        body = {
            "kind": kind,
            "run_id": run_id,
            "fingerprint": fingerprint,
            "scope_sha256": scope_sha256,
            "payload": dict(payload or {}),
        }
        return Proof(
            kind=kind,
            run_id=run_id,
            fingerprint=fingerprint,
            scope_sha256=scope_sha256,
            payload=body["payload"],
            token=sha256_canonical(body),
        )

    def assert_binds(
        self,
        *,
        kind: str,
        run_id: str,
        fingerprint: str,
        scope_sha256: str,
    ) -> None:
        """Reject forged or reused proofs for the wrong run/state."""
        if self.kind != kind:
            raise PolicyViolation(f"proof kind mismatch: {self.kind} != {kind}")
        if self.run_id != run_id:
            raise PolicyViolation("proof run_id mismatch")
        if self.fingerprint != fingerprint:
            raise PolicyViolation("proof fingerprint mismatch")
        if self.scope_sha256 != scope_sha256:
            raise PolicyViolation("proof scope_sha256 mismatch")
        expected = Proof.issue(
            self.kind,
            run_id=self.run_id,
            fingerprint=self.fingerprint,
            scope_sha256=self.scope_sha256,
            payload=self.payload,
        )
        if expected.token != self.token:
            raise PolicyViolation("proof token tampered")
