"""Unit tests for canonical FamilyStatus semantics (fail-closed)."""

from __future__ import annotations

import pytest

from app.modules.ai_package_v1.domain.enums import FamilyStatus
from app.modules.ai_package_v1.export.family_status import family_status_for_gap_entry

pytestmark = pytest.mark.unit


def test_family_status_enum_is_closed_set() -> None:
    values = {member.value for member in FamilyStatus}
    assert values == {
        "COMPLETE",
        "PARTIAL",
        "GAP",
        "UNSUPPORTED",
        "FAILED",
    }
    assert "UNKNOWN" not in values


def test_unknown_family_status_token_fails_closed_to_gap() -> None:
    assert family_status_for_gap_entry("UNKNOWN") == FamilyStatus.GAP
    assert family_status_for_gap_entry("NOT_A_STATUS") == FamilyStatus.GAP


def test_valid_family_status_tokens_parse() -> None:
    for token in ("COMPLETE", "PARTIAL", "GAP", "UNSUPPORTED", "FAILED"):
        assert family_status_for_gap_entry(token) == FamilyStatus(token)
