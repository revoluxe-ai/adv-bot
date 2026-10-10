"""Domain invariant violations for decision-experiment memory."""

from __future__ import annotations


class DecisionExperimentMemoryError(Exception):
    """Base error for decision-experiment memory domain."""


class IdentityInvariantError(DecisionExperimentMemoryError):
    """Raised when decision/experiment identity rules are violated."""


class PlanInvariantError(DecisionExperimentMemoryError):
    """Raised when experiment plan freeze or revision rules are violated."""


class ExposureInvariantError(DecisionExperimentMemoryError):
    """Raised when exposure or apply linkage rules are violated."""
