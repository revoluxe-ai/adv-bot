"""Deterministic canonical JSON semantics."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

import pytest

from app.modules.decision_experiment_memory.canonical_json import canonical_sha256
from app.modules.decision_experiment_memory.domain.enums import ExperimentDesign

pytestmark = pytest.mark.unit


class _SampleEnum(Enum):
    A = "a"


def test_dict_key_order_invariant() -> None:
    a = {"z": 1, "a": {"y": 2, "b": 3}}
    b = {"a": {"b": 3, "y": 2}, "z": 1}
    assert canonical_sha256(a) == canonical_sha256(b)


def test_tuple_and_enum_and_decimal_and_datetime() -> None:
    when = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    payload = {
        "tags": ("a", "b"),
        "design": ExperimentDesign.RANDOMIZED_AB,
        "amount": Decimal("1.25"),
        "at": when,
        "nested": _SampleEnum.A,
    }
    digest = canonical_sha256(payload)
    assert len(digest) == 64
