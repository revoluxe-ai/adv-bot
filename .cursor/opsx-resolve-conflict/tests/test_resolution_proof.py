"""Adversarial tests for the R11 namespace-closed resolution proof."""

from __future__ import annotations

import pytest

from opsx_conflict.errors import StopRequired
from opsx_conflict.resolution_proof import prove_text_resolution


BASE = 'def base():\n    return "base"\n'
STAGE2 = BASE + "\ndef guard_enabled(value):\n    return value > 0\n"
STAGE3 = BASE + "\ndef retry_limit(value):\n    return value + 1\n"
VALID = STAGE2 + "\ndef retry_limit(value):\n    return value + 1\n"


def _prove(resolution: str):
    return prove_text_resolution(
        path="service.py",
        resolution=resolution,
        stage_blobs={1: BASE, 2: STAGE2, 3: STAGE3},
        topology="modify/modify",
    )


def test_exact_append_only_ast_union_is_accepted() -> None:
    proof = _prove(VALID)
    assert proof.strategy == "namespace_closed_comment_exact_ast_union"
    assert proof.preserved_from_stage2 == ("guard_enabled",)
    assert proof.preserved_from_stage3 == ("retry_limit",)


@pytest.mark.parametrize(
    "attack",
    [
        "# guard_enabled retry_limit\npass\n",
        BASE + "\ndef guard_enabled(value):\n    pass\n\ndef retry_limit(value):\n    pass\n",
        BASE + "\ndef guard_enabled(value):\n    return False\n\ndef retry_limit(value):\n    return value + 1\n",
        BASE + "\nif False:\n    def guard_enabled():\n        perform_safe_write()\n",
        STAGE2,
        STAGE3,
    ],
)
def test_comments_dead_code_and_changed_behavior_are_rejected(attack: str) -> None:
    with pytest.raises(StopRequired) as exc:
        _prove(attack)
    assert exc.value.reason.startswith(("STRUCTURAL_", "SEMANTIC_"))


def test_modified_existing_guard_is_outside_autonomous_class() -> None:
    base = "def write():\n    if enabled:\n        persist()\n"
    stage2 = "def write():\n    if True:\n        persist()\n"
    stage3 = "def write():\n    if enabled:\n        retry()\n        persist()\n"
    with pytest.raises(StopRequired) as exc:
        prove_text_resolution(
            path="service.py",
            resolution="def write():\n    persist()\n",
            stage_blobs={1: base, 2: stage2, 3: stage3},
            topology="modify/modify",
        )
    assert exc.value.reason in {
        "STRUCTURAL_PROOF_BASE_MODIFIED",
        "STRUCTURAL_PROOF_ALLOWLIST_VIOLATION",
        "STRUCTURAL_PROOF_EFFECTFUL_FUNCTION_BODY",
        "STRUCTURAL_PROOF_EXTERNAL_EFFECT_OR_DYNAMIC_ACCESS",
    }


def test_non_python_and_binary_inputs_stop_before_write() -> None:
    with pytest.raises(StopRequired) as non_python:
        prove_text_resolution(
            path="asset.bin",
            resolution="x",
            stage_blobs={1: "a", 2: "b", 3: "c"},
            topology="modify/modify",
        )
    assert non_python.value.reason == "STRUCTURAL_PROOF_UNSUPPORTED_FILE_TYPE"

    with pytest.raises(StopRequired) as binary:
        prove_text_resolution(
            path="service.py",
            resolution=VALID,
            stage_blobs={1: BASE, 2: STAGE2 + "\x00", 3: STAGE3},
            topology="modify/modify",
        )
    assert binary.value.reason == "STRUCTURAL_PROOF_BINARY_CONTENT"


def test_global_binding_collision_and_cross_side_dependency_stop() -> None:
    base = "MODE = 1\n"
    stage2 = base + "\ndef MODE():\n    return 2\n"
    stage3 = base + "\ndef use_mode():\n    return MODE + 1\n"
    with pytest.raises(StopRequired) as collision:
        prove_text_resolution(
            path="service.py",
            resolution=stage2 + "\ndef use_mode():\n    return MODE + 1\n",
            stage_blobs={1: base, 2: stage2, 3: stage3},
            topology="modify/modify",
        )
    assert collision.value.reason in {
        "STRUCTURAL_PROOF_GLOBAL_READ",
        "STRUCTURAL_PROOF_ALLOWLIST_VIOLATION",
        "STRUCTURAL_PROOF_EFFECTFUL_FUNCTION_BODY",
        "STRUCTURAL_PROOF_EXTERNAL_EFFECT_OR_DYNAMIC_ACCESS",
    }

    stage2 = base + "\ndef produced(value):\n    return value + 1\n"
    stage3 = base + "\ndef consumed(value):\n    return produced(value)\n"
    with pytest.raises(StopRequired) as dependency:
        prove_text_resolution(
            path="service.py",
            resolution=stage2 + "\ndef consumed(value):\n    return produced(value)\n",
            stage_blobs={1: base, 2: stage2, 3: stage3},
            topology="modify/modify",
        )
    assert dependency.value.reason.startswith("STRUCTURAL_PROOF_")


@pytest.mark.parametrize(
    ("stage2_suffix", "reason"),
    [
        ("\n# coding: latin-1\ndef safe(value):\n    return value\n", "SOURCE_DIRECTIVE"),
        ("\ndef safe(value):  # noqa\n    return value\n", "SOURCE_DIRECTIVE"),
        (
            "\ndef safe(value):\n    shared.append(value)\n    return value\n",
            "EFFECT",
        ),
    ],
)
def test_source_directives_and_external_effects_stop(
    stage2_suffix: str,
    reason: str,
) -> None:
    stage2 = BASE + stage2_suffix
    stage3 = BASE + "\ndef other(value):\n    return value\n"
    with pytest.raises(StopRequired) as exc:
        prove_text_resolution(
            path="service.py",
            resolution=stage2 + "\ndef other(value):\n    return value\n",
            stage_blobs={1: BASE, 2: stage2, 3: stage3},
            topology="modify/modify",
        )
    allowed = {
        "STRUCTURAL_PROOF_ALLOWLIST_VIOLATION",
        "STRUCTURAL_PROOF_EFFECTFUL_FUNCTION_BODY",
        "STRUCTURAL_PROOF_EXTERNAL_EFFECT_OR_DYNAMIC_ACCESS",
        "STRUCTURAL_PROOF_GLOBAL_READ",
        "STRUCTURAL_PROOF_SOURCE_DIRECTIVE_CHANGED",
        "STRUCTURAL_PROOF_UNSUPPORTED_ENCODING_DIRECTIVE",
    }
    assert reason in exc.value.reason or exc.value.reason in allowed


def test_non_utf8_encoding_cookie_stops() -> None:
    stage2 = "# coding: latin-1\n" + BASE + "\ndef safe(value):\n    return value\n"
    stage3 = BASE + "\ndef other(value):\n    return value\n"
    with pytest.raises(StopRequired) as exc:
        prove_text_resolution(
            path="service.py",
            resolution=stage2 + "\ndef other(value):\n    return value\n",
            stage_blobs={1: BASE, 2: stage2, 3: stage3},
            topology="modify/modify",
        )
    assert exc.value.reason == "STRUCTURAL_PROOF_UNSUPPORTED_ENCODING_DIRECTIVE"


def test_base_namespace_observation_stops_autonomous_union() -> None:
    """``globals()`` observers make AST-union semantically unsafe."""
    base = (
        "def feature_count():\n"
        "    return len([n for n in globals() if n.startswith('feature_')])\n"
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
        "STRUCTURAL_PROOF_NAMESPACE_OBSERVATION",
    }


def test_eval_dynamic_lookup_stops_autonomous_union() -> None:
    """``eval`` must not allow false-positive AST-union success."""
    base = (
        "def probe():\n"
        "    try:\n"
        "        return eval('feature_a')\n"
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
        "STRUCTURAL_PROOF_NAMESPACE_OBSERVATION",
    }


def test_reserved_module_name_binding_stops_autonomous_union() -> None:
    """Implicit module bindings such as ``__name__`` are not autonomous-safe."""
    base = "def base():\n    return 1\n"
    stage2 = base + "\ndef __name__():\n    return 2\n"
    stage3 = base + "\ndef other():\n    return 3\n"
    with pytest.raises(StopRequired) as exc:
        prove_text_resolution(
            path="service.py",
            resolution=stage2 + "\ndef other():\n    return 3\n",
            stage_blobs={1: base, 2: stage2, 3: stage3},
            topology="modify/modify",
        )
    assert exc.value.reason == "STRUCTURAL_PROOF_RESERVED_MODULE_BINDING"


@pytest.mark.parametrize(
    ("base", "stage2_suffix", "stage3_suffix"),
    [
        (
            "",
            "\ndef __getattr__(name):\n    return 1\n",
            "\ndef feature():\n    return 2\n",
        ),
        (
            "def __dir__():\n    return ()\n",
            "\ndef left():\n    return 1\n",
            "\ndef right():\n    return 2\n",
        ),
        (
            "__all__ = ()\n",
            "\ndef left():\n    return 1\n",
            "\ndef right():\n    return 2\n",
        ),
    ],
)
def test_module_namespace_hooks_stop_autonomous_union(
    base: str,
    stage2_suffix: str,
    stage3_suffix: str,
) -> None:
    stage2 = base + stage2_suffix
    stage3 = base + stage3_suffix
    with pytest.raises(StopRequired) as exc:
        prove_text_resolution(
            path="service.py",
            resolution=stage2 + stage3_suffix,
            stage_blobs={1: base, 2: stage2, 3: stage3},
            topology="modify/modify",
        )
    assert exc.value.reason in {
        "STRUCTURAL_PROOF_ALLOWLIST_VIOLATION",
        "STRUCTURAL_PROOF_RESERVED_MODULE_BINDING",
        "STRUCTURAL_PROOF_MODULE_NAMESPACE_HOOK",
    }


@pytest.mark.parametrize(
    "comment",
    [
        "# pragma: no branch",
        "# nosec",
        "# pyre-ignore",
        "# pytype: disable=attribute-error",
        "# unknown-tool: suppress",
    ],
)
def test_any_added_comment_stops_unknown_directive_bypass(comment: str) -> None:
    stage2 = BASE + f"\n{comment}\ndef safe(value):\n    return value\n"
    stage3 = BASE + "\ndef other(value):\n    return value\n"
    with pytest.raises(StopRequired) as exc:
        prove_text_resolution(
            path="service.py",
            resolution=stage2 + "\ndef other(value):\n    return value\n",
            stage_blobs={1: BASE, 2: stage2, 3: stage3},
            topology="modify/modify",
        )
    assert exc.value.reason in {
        "STRUCTURAL_PROOF_SOURCE_COMMENT_CHANGED",
        "STRUCTURAL_PROOF_SOURCE_DIRECTIVE_CHANGED",
    }
