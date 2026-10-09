"""Slice A scenario evidence hooks (S04, S07, S22, S30–S33)."""

from __future__ import annotations

import pytest

from app.modules.wb_sky_control_plane.apply.binding import binding_hint_mismatches
from app.modules.wb_sky_control_plane.apply.enums import ApplyReasonCode
from app.modules.wb_sky_control_plane.apply.models.binding import ApplyBindingHintsV1

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("scenario_id", "hints", "expected"),
    [
        ("S07", ApplyBindingHintsV1(semantic_digest="sd1_wrong"), ApplyReasonCode.CHANGESET_DIGEST_MISMATCH),
        ("S33", ApplyBindingHintsV1(semantic_digest="sd1_wrong"), ApplyReasonCode.CHANGESET_DIGEST_MISMATCH),
    ],
)
def test_digest_hint_mismatch(scenario_id: str, hints: ApplyBindingHintsV1, expected: ApplyReasonCode) -> None:
    reason = binding_hint_mismatches(
        hints,
        semantic_digest="sd1_expected",
        preview_digest="pd1_expected",
    )
    assert reason == expected
