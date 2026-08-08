"""R20 acceptance closures for the independent R19 rejection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from opsx_conflict.errors import StopRequired
from opsx_conflict.proofs import Proof
from opsx_conflict.validation import run_frozen_check
import opsx_conflict.validation as validation_module

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_packaged_evidence_digest_matches_manifest_and_anchor() -> None:
    """In-tree evidence may not claim a foreign package_digest."""
    manifest = json.loads((PACKAGE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    anchor = json.loads((PACKAGE_ROOT / "TRUST_ANCHOR.json").read_text(encoding="utf-8"))
    clean = json.loads(
        (PACKAGE_ROOT / "CLEAN_UNPACK_TEST_REPORT.json").read_text(encoding="utf-8")
    )
    index = json.loads((PACKAGE_ROOT / "PACKAGE_INDEX.json").read_text(encoding="utf-8"))
    digest = manifest["package_digest"]
    assert anchor["package_digest"] == digest
    assert clean["package_digest"] == digest
    assert index["package_digest"] == digest
    assert clean.get("archive_binding") == "external_test_report_only"
    assert index.get("archive_binding") == "external_test_report_only"
    assert clean.get("archive_sha256") in (None, "")
    assert index.get("archive_sha256") in (None, "")


def test_poetry_missing_still_blocks_unpatched_executor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail-closed: real frozen poetry checks STOP when poetry is absent."""
    monkeypatch.setattr(validation_module.shutil, "which", lambda *_a, **_k: None)
    fingerprints = {"app/x.py": "a" * 64}
    plan = Proof.issue(
        "frozen_test_plan",
        run_id="r20",
        fingerprint="f" * 64,
        scope_sha256="s" * 64,
        payload={
            "content_fingerprints": fingerprints,
            "checks": [
                {
                    "check_id": "pytest-unit",
                    "tool": "pytest",
                    "wave": "A",
                    "argv": ["poetry", "run", "pytest", "-m", "unit"],
                    "timeout_seconds": 60,
                    "rel_nodes": ["app/x.py"],
                }
            ],
        },
    )
    snapshot = tmp_path / "snap"
    (snapshot / "app").mkdir(parents=True)
    (snapshot / "app" / "x.py").write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(StopRequired) as exc:
        run_frozen_check(
            plan=plan,
            check_id="pytest-unit",
            snapshot=snapshot,
            unit_wave_passed=set(),
            content_fingerprints=fingerprints,
            sandbox={
                "runner": str(tmp_path / "runner.py"),
                "sha256": "b" * 64,
                "spawn_argv_prefix": [str(tmp_path / "runner.py")],
                "enforcement_level": "OS_VERIFIED",
                "network": "DENY",
                "filesystem": "SNAPSHOT_ONLY",
                "protocol": "opsx-sandbox-path-confinement/v1",
            },
        )
    assert exc.value.reason == "ENVIRONMENT_OR_CREDENTIAL_BLOCK"


def test_go_fixture_poetry_stub_is_installed() -> None:
    """Document that GO fixtures stub poetry via validation.shutil.which."""
    source = (
        PACKAGE_ROOT / "tests" / "test_orchestrator_go.py"
    ).read_text(encoding="utf-8")
    assert 'cmd == "poetry"' in source
    assert "fake-poetry" in source
    assert 'setattr(validation_module.shutil, "which"' in source
