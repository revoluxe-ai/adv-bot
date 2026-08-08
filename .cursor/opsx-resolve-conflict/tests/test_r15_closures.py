"""R15 acceptance closures for the independent R14 rejection."""

from __future__ import annotations

from validation_registry_helpers import install_actual_registry

from pathlib import Path

import pytest

from opsx_conflict.errors import StopRequired
from opsx_conflict.resolution_proof import prove_text_resolution
from opsx_conflict.validation import FrozenTestPlanCompiler


def test_import_alias_dynamic_lookup_stops_autonomous_union() -> None:
    """``from builtins import globals as g`` must stop AST-union."""
    base = (
        "from builtins import globals as g\n"
        "\n"
        "def probe():\n"
        "    return 'feature_a' in g()\n"
    )
    stage2 = base + "\ndef feature_a():\n    return 1\n"
    stage3 = base + "\ndef feature_b():\n    return 2\n"
    with pytest.raises(StopRequired) as exc:
        prove_text_resolution(
            path="service.py",
            resolution=stage2 + "\ndef feature_b():\n    return 2\n",
            stage_blobs={1: base, 2: stage2, 3: stage3},
            topology="modify/modify",
        )
    assert exc.value.reason in {
        "STRUCTURAL_PROOF_ALLOWLIST_VIOLATION",
        "STRUCTURAL_PROOF_EFFECTFUL_FUNCTION_BODY",
        "STRUCTURAL_PROOF_EXTERNAL_EFFECT_OR_DYNAMIC_ACCESS",
        "STRUCTURAL_PROOF_DYNAMIC_ALIAS",
        "STRUCTURAL_PROOF_NAMESPACE_OBSERVATION",
        "STRUCTURAL_PROOF_DYNAMIC_IMPORT",
    }


def test_assignment_alias_eval_stops_autonomous_union() -> None:
    """``e = eval`` aliases must not pass structural proof."""
    base = (
        "e = eval\n"
        "\n"
        "def probe():\n"
        "    try:\n"
        "        return e('feature_a')\n"
        "    except NameError:\n"
        "        return 'missing'\n"
    )
    stage2 = base + "\ndef feature_a():\n    return 1\n"
    stage3 = base + "\ndef feature_b():\n    return 2\n"
    with pytest.raises(StopRequired) as exc:
        prove_text_resolution(
            path="service.py",
            resolution=stage2 + "\ndef feature_b():\n    return 2\n",
            stage_blobs={1: base, 2: stage2, 3: stage3},
            topology="modify/modify",
        )
    assert exc.value.reason in {
        "STRUCTURAL_PROOF_ALLOWLIST_VIOLATION",
        "STRUCTURAL_PROOF_EFFECTFUL_FUNCTION_BODY",
        "STRUCTURAL_PROOF_EXTERNAL_EFFECT_OR_DYNAMIC_ACCESS",
        "STRUCTURAL_PROOF_DYNAMIC_ALIAS",
        "STRUCTURAL_PROOF_NAMESPACE_OBSERVATION",
    }


def test_missing_targeted_tests_block_inventory(
    tmp_path: Path,
) -> None:
    """Unknown targeted applicability must BLOCK, not NOT_APPLICABLE."""
    root = tmp_path
    registry, hashes = install_actual_registry(root)
    with pytest.raises(StopRequired) as exc:
        FrozenTestPlanCompiler(
            run_id="r1",
            fingerprint="f" * 64,
            scope_sha256="s" * 64,
            content_fingerprints={"app/service.py": "c" * 64},
            registry_path=registry,
            frozen_contract_hashes=hashes,
            targeted_nodes=("app/service.py",),
            adjacent_nodes=(),
        ).compile()
    assert exc.value.reason == "OPSX_VALIDATION_INVENTORY_BLOCKED"
    blocked = exc.value.details.get("blocked", [])
    categories = {row.get("category") for row in blocked}
    assert "targeted_symbol_tests" in categories
    assert "interface_contract_tests" in categories
