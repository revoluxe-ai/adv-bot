"""R18 acceptance closures for the independent R17 rejection."""

from __future__ import annotations

from validation_registry_helpers import install_actual_registry

import hashlib
import json
import os
from pathlib import Path

import pytest

from opsx_conflict.errors import StopRequired
from opsx_conflict.git_typed import resolve_trusted_git
from opsx_conflict.resolution_proof import prove_text_resolution
from opsx_conflict.validation import FrozenTestPlanCompiler


def _union(base: str) -> tuple[str, str, str]:
    """Build stage2/stage3/union texts for append-only AST union probes."""
    stage2 = base + "\ndef feature_a():\n    return 1\n"
    stage3 = base + "\ndef feature_b():\n    return 2\n"
    union = stage2 + "\ndef feature_b():\n    return 2\n"
    return stage2, stage3, union


def test_getattribute_globals_bypass_stops_closed_allowlist() -> None:
    """``__getattribute__('__globals__')`` is outside the closed AST grammar."""
    base = (
        "def probe():\n"
        "    return 'feature_a' in probe.__getattribute__('__globals__')\n"
    )
    stage2, stage3, union = _union(base)
    with pytest.raises(StopRequired) as exc:
        prove_text_resolution(
            path="service.py",
            resolution=union,
            stage_blobs={1: base, 2: stage2, 3: stage3},
            topology="modify/modify",
        )
    assert exc.value.reason == "STRUCTURAL_PROOF_ALLOWLIST_VIOLATION"


def test_name_only_symbol_reference_does_not_prove_role(
    tmp_path: Path,
) -> None:
    """Import + bind without call/assert must not complete role inventory."""
    registry, hashes = install_actual_registry(tmp_path)
    service = tmp_path / "app" / "service.py"
    service.parent.mkdir(parents=True)
    service.write_text("def feature():\n    return 1\n", encoding="utf-8")
    unit = tmp_path / "tests" / "unit"
    unit.mkdir(parents=True)
    (unit / "test_unrelated.py").write_text(
        "from app.service import feature\n\ndef test_unrelated():\n    _ = feature\n    assert 2 + 2 == 4\n",
        encoding="utf-8",
    )
    (unit / "test_unrelated.opsx-roles.json").write_text(
        json.dumps(
            {
                "schema": "opsx-resolve-conflict/test-roles/v1",
                "roles": ["targeted_symbol"],
                "covers_paths": ["app/service.py"],
                "covers_symbols": ["feature"],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(StopRequired) as exc:
        FrozenTestPlanCompiler(
            run_id="r1",
            fingerprint="f" * 64,
            scope_sha256="s" * 64,
            content_fingerprints={"app/service.py": "c" * 64},
            registry_path=registry,
            frozen_contract_hashes=hashes,
            targeted_nodes=("app/service.py",),
        ).compile()
    assert exc.value.reason == "OPSX_VALIDATION_INVENTORY_BLOCKED"


def test_git_trust_unbound_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production must refuse OPSX_CONFLICT_GIT_TRUST_UNBOUND."""
    monkeypatch.setenv("OPSX_CONFLICT_GIT_TRUST_UNBOUND", "1")
    monkeypatch.delenv("OPSX_CONFLICT_GIT_TRUST_DIGEST", raising=False)
    with pytest.raises(StopRequired) as exc:
        resolve_trusted_git()
    assert exc.value.reason == "GIT_TRUST_UNBOUND_FORBIDDEN"


def test_git_trust_digest_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pinned digest allows Git resolution."""
    monkeypatch.delenv("OPSX_CONFLICT_GIT_TRUST_UNBOUND", raising=False)
    # conftest already pins digest; ensure identity resolves.
    identity = resolve_trusted_git()
    assert identity["trust"] == "DIGEST_BOUND"
    assert identity["sha256"] == os.environ["OPSX_CONFLICT_GIT_TRUST_DIGEST"]
