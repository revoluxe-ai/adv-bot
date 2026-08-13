"""R16 acceptance closures for the independent R15 rejection."""

from __future__ import annotations

from validation_registry_helpers import install_actual_registry

import hashlib
import json
from pathlib import Path

import pytest

from opsx_conflict.errors import StopRequired
from opsx_conflict.resolution_proof import prove_text_resolution
from opsx_conflict.validation import FrozenTestPlanCompiler


def _union_with_base(base: str) -> tuple[str, str, str]:
    """Build stage2/stage3/union texts for append-only AST union probes."""
    stage2 = base + "\ndef feature_a():\n    return 1\n"
    stage3 = base + "\ndef feature_b():\n    return 2\n"
    union = stage2 + "\ndef feature_b():\n    return 2\n"
    return stage2, stage3, union


@pytest.mark.parametrize(
    "base",
    [
        "g = (globals,)[0]\n\ndef probe():\n    return 'feature_a' in g()\n",
        "g = [globals][0]\n\ndef probe():\n    return 'feature_a' in g()\n",
        'g = {"x": globals}["x"]\n\ndef probe():\n    return "feature_a" in g()\n',
        "g, = (globals,)\n\ndef probe():\n    return 'feature_a' in g()\n",
        (
            "def wrap():\n"
            "    return globals\n"
            "\n"
            "g = wrap()\n"
            "\n"
            "def probe():\n"
            "    return 'feature_a' in g()\n"
        ),
    ],
)
def test_container_and_expression_dynamic_aliases_stop(base: str) -> None:
    """First-class dynamic primitives in containers/expressions must STOP."""
    stage2, stage3, union = _union_with_base(base)
    with pytest.raises(StopRequired) as exc:
        prove_text_resolution(
            path="service.py",
            resolution=union,
            stage_blobs={1: base, 2: stage2, 3: stage3},
            topology="modify/modify",
        )
    assert exc.value.reason in {
        "STRUCTURAL_PROOF_ALLOWLIST_VIOLATION",
        "STRUCTURAL_PROOF_EFFECTFUL_FUNCTION_BODY",
        "STRUCTURAL_PROOF_EXTERNAL_EFFECT_OR_DYNAMIC_ACCESS",
        "STRUCTURAL_PROOF_NAMESPACE_OBSERVATION",
        "STRUCTURAL_PROOF_DYNAMIC_ALIAS",
    }


def _registry_fixture(root: Path) -> tuple[Path, dict[str, str]]:
    """Install actual FULL registry with pack inventory hashes."""
    return install_actual_registry(root)


def _write_service(root: Path) -> None:
    service = root / "app" / "service.py"
    service.parent.mkdir(parents=True, exist_ok=True)
    service.write_text("def feature():\n    return 1\n", encoding="utf-8")


def _install_extra_adapters(root: Path, hashes: dict[str, str]) -> Path:
    """R28: unknown checks have no closed adapter; keep actual four-check registry."""
    registry, fresh = install_actual_registry(root)
    hashes.clear()
    hashes.update(fresh)
    return registry


def test_filename_only_test_cannot_prove_three_roles(tmp_path: Path) -> None:
    """One filename-matched unit test must not auto-prove interface/contour."""
    registry, hashes = _registry_fixture(tmp_path)
    _write_service(tmp_path)
    unit = tmp_path / "tests" / "unit"
    unit.mkdir(parents=True)
    (unit / "test_service.py").write_text(
        "def test_service():\n    assert True\n",
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
            interface_nodes=("tests/unit/test_service.py",),
            contour_nodes=("tests/unit/test_service.py",),
        ).compile()
    assert exc.value.reason == "OPSX_VALIDATION_INVENTORY_BLOCKED"
    blocked = exc.value.details.get("blocked", [])
    categories = {row.get("category") for row in blocked}
    assert "targeted_symbol_tests" in categories
    assert "interface_contract_tests" in categories
    assert "affected_contour_tests" in categories


def test_multi_role_metadata_requires_explicit_declaration(tmp_path: Path) -> None:
    """One sidecar may not claim multiple roles; split tests instead."""
    registry, hashes = _registry_fixture(tmp_path)
    registry = _install_extra_adapters(tmp_path, hashes)
    _write_service(tmp_path)
    unit = tmp_path / "tests" / "unit"
    unit.mkdir(parents=True)
    (unit / "test_service.py").write_text(
        "from app.service import feature\n\ndef test_service():\n    assert feature() == 1\n",
        encoding="utf-8",
    )
    (unit / "test_service.opsx-roles.json").write_text(
        json.dumps(
            {
                "schema": "opsx-resolve-conflict/test-roles/v1",
                "roles": [
                    "targeted_symbol",
                    "interface_contract",
                    "affected_contour",
                ],
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
    assert exc.value.reason == "OPSX_VALIDATION_MULTI_ROLE_FORBIDDEN"


def test_role_bound_separate_tests_compile(tmp_path: Path) -> None:
    """Distinct role-bound tests with metadata compile a complete inventory."""
    registry, hashes = _registry_fixture(tmp_path)
    registry = _install_extra_adapters(tmp_path, hashes)
    _write_service(tmp_path)
    unit = tmp_path / "tests" / "unit"
    unit.mkdir(parents=True)
    for name, role in (
        ("test_service.py", "targeted_symbol"),
        ("test_service_interface.py", "interface_contract"),
        ("test_service_contour.py", "affected_contour"),
    ):
        (unit / name).write_text(
            "from app.service import feature\n\ndef test_ok():\n    assert feature() == 1\n",
            encoding="utf-8",
        )
        (unit / name.replace(".py", ".opsx-roles.json")).write_text(
            json.dumps(
                {
                    "schema": "opsx-resolve-conflict/test-roles/v1",
                    "roles": [role],
                    "covers_paths": ["app/service.py"],
                    "covers_symbols": ["feature"],
                }
            ),
            encoding="utf-8",
        )
    proof = FrozenTestPlanCompiler(
        run_id="r1",
        fingerprint="f" * 64,
        scope_sha256="s" * 64,
        content_fingerprints={"app/service.py": "c" * 64},
        registry_path=registry,
        frozen_contract_hashes=hashes,
        targeted_nodes=("app/service.py",),
        interface_nodes=("tests/unit/test_service_interface.py",),
        contour_nodes=("tests/unit/test_service_contour.py",),
    ).compile()
    assert proof.payload["validation_inventory_complete"] is True
    selected = set(proof.payload["selected_check_ids"])
    assert "pytest-targeted" in selected
    assert "pytest-interface" in selected
    assert "pytest-contour" in selected


def test_discovered_unmapped_registry_check_blocks(tmp_path: Path) -> None:
    """Unknown FULL-wave checks without closed typed adapter fail closed."""
    registry, hashes = _registry_fixture(tmp_path)
    registry.write_text(
        """
version: 1
modes:
  FULL:
    waves:
      - id: A
        checks: [pyright-strict, mypy, pytest-unit, custom-gate]
      - id: B
        after: [pytest-unit]
        require_status: PASS
        checks: [pytest-full]
checks:
  pyright-strict:
    task_type: shell
    pack: .cursor/static-check/checks/pyright-strict
  mypy:
    task_type: shell
    pack: .cursor/static-check/checks/mypy
  pytest-unit:
    task_type: shell
    pack: .cursor/static-check/checks/pytest-unit
  pytest-full:
    task_type: shell
    pack: .cursor/static-check/checks/pytest-full
  custom-gate:
    task_type: shell
    pack: .cursor/static-check/checks/custom-gate
""".lstrip(),
        encoding="utf-8",
    )
    hashes[registry.relative_to(tmp_path).as_posix()] = hashlib.sha256(
        registry.read_bytes()
    ).hexdigest()
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
    assert exc.value.reason == "FULL_VALIDATION_ADAPTER_UNAVAILABLE"
    assert exc.value.details.get("check_id") == "custom-gate"
