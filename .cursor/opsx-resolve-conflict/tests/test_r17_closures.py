"""R17 acceptance closures for the independent R16 rejection."""

from __future__ import annotations

from validation_registry_helpers import install_actual_registry

import hashlib
import json
from pathlib import Path

import pytest

from opsx_conflict.errors import StopRequired
from opsx_conflict.resolution_proof import prove_text_resolution
from opsx_conflict.validation import FrozenTestPlanCompiler


def _union(base: str) -> tuple[str, str, str]:
    stage2 = base + "\ndef feature_a():\n    return 1\n"
    stage3 = base + "\ndef feature_b():\n    return 2\n"
    union = stage2 + "\ndef feature_b():\n    return 2\n"
    return stage2, stage3, union


@pytest.mark.parametrize(
    "base",
    [
        (
            "import sys\n"
            "\n"
            "def probe():\n"
            "    return 'feature_a' in sys._getframe().f_globals\n"
        ),
        (
            'g = __builtins__["globals"]\n'
            "\n"
            "def probe():\n"
            "    return 'feature_a' in g()\n"
        ),
        (
            'g = __builtins__.__getitem__("globals")\n'
            "\n"
            "def probe():\n"
            "    return 'feature_a' in g()\n"
        ),
        (
            "import operator\n"
            "\n"
            "def probe():\n"
            "    getter = operator.attrgetter('f_globals')\n"
            "    return getter\n"
        ),
    ],
)
def test_frame_builtins_reflection_namespace_access_stops(base: str) -> None:
    """Frame/builtins/reflection namespace access is outside autonomous allowlist."""
    stage2, stage3, union = _union(base)
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
        "STRUCTURAL_PROOF_DYNAMIC_IMPORT",
        "STRUCTURAL_PROOF_DYNAMIC_ALIAS",
    }


def _full_registry(root: Path) -> tuple[Path, dict[str, str]]:
    """Install actual FULL registry with pack inventory hashes."""
    return install_actual_registry(root)



def test_arbitrary_role_sidecar_does_not_prove_coverage(tmp_path: Path) -> None:
    """Unrelated green test with multi-role metadata must not complete inventory."""
    registry, hashes = _full_registry(tmp_path)
    service = tmp_path / "app" / "service.py"
    service.parent.mkdir(parents=True)
    service.write_text("def feature():\n    return 1\n", encoding="utf-8")
    unit = tmp_path / "tests" / "unit"
    unit.mkdir(parents=True)
    (unit / "test_unrelated.py").write_text(
        "def test_unrelated():\n    assert 2 + 2 == 4\n",
        encoding="utf-8",
    )
    (unit / "test_unrelated.opsx-roles.json").write_text(
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
    assert exc.value.reason in {
        "OPSX_VALIDATION_INVENTORY_BLOCKED",
        "OPSX_VALIDATION_MULTI_ROLE_FORBIDDEN",
    }


def test_symbol_bound_roles_compile(tmp_path: Path) -> None:
    """Role metadata with proven covers_symbols compiles a complete inventory."""
    registry, hashes = _full_registry(tmp_path)
    service = tmp_path / "app" / "service.py"
    service.parent.mkdir(parents=True)
    service.write_text("def feature():\n    return 1\n", encoding="utf-8")
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
    ).compile()
    assert proof.payload["validation_inventory_complete"] is True


def test_pipeline_graph_gates_block_without_adapters(tmp_path: Path) -> None:
    """Mentioned pipeline gates without typed adapters must BLOCK inventory."""
    registry, hashes = _full_registry(tmp_path)
    graph = tmp_path / ".cursor" / "pipeline" / "GRAPH.md"
    graph.parent.mkdir(parents=True)
    graph.write_text(
        "# graph\n\n- /opsx-verify\n- /opsx-external-call-coverage\n",
        encoding="utf-8",
    )
    service = tmp_path / "app" / "service.py"
    service.parent.mkdir(parents=True)
    service.write_text("def feature():\n    return 1\n", encoding="utf-8")
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
    blocked = exc.value.details.get("blocked", [])
    assert any(
        row.get("category") == "opsx_pipeline_conditional_gates" for row in blocked
    )
