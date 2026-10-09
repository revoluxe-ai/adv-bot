"""Compact experiment memory index entries (reader contract; Slice F export deferred)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExperimentMemoryIndexEntry:
    """Structured index row for similar/active experiment retrieval."""

    experiment_id: str
    decision_id: str
    shop_id: str
    intervention_signature_digest: str
    experiment_design: str
    treatment_mode: str
    execution_state: str
    outcome: str
    confounder_flags: tuple[str, ...] = ()
