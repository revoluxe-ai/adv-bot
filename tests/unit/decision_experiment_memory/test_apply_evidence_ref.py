"""ApplyEvidenceRef contract literals."""

from __future__ import annotations

import pytest

from app.modules.decision_experiment_memory.domain.refs import ApplyEvidenceRef

pytestmark = pytest.mark.unit


def test_default_authority_kind_is_apply_authority() -> None:
    ref = ApplyEvidenceRef(apply_evidence_id="a1")
    assert ref.authority_kind == "APPLY_AUTHORITY"
    assert ref.evidence_digest is None
