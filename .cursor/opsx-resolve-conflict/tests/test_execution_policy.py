"""Typed FULL-validation registry and frozen argv policy tests (R28)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from opsx_conflict.runtime import (
    PolicyViolation,
    FrozenTestPlanCompiler,
    assert_frozen_argv,
    effective_final_gate,
)
from opsx_conflict.validation import _load_registry_checks
from validation_registry_helpers import install_actual_registry


def _hash_static_check_tree(root: Path) -> dict[str, str]:
    """Hash every file under .cursor/static-check for frozen contract maps."""
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (root / ".cursor" / "static-check").rglob("*")
        if path.is_file()
    }


@pytest.fixture()
def frozen_plan(tmp_path: Path):
    registry, hashes = install_actual_registry(tmp_path)
    app = tmp_path / "app"
    app.mkdir(parents=True)
    (app / "x.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    unit = tmp_path / "tests" / "unit"
    unit.mkdir(parents=True)
    for name, roles in (
        ("test_x.py", ["targeted_symbol"]),
        ("test_x_interface.py", ["interface_contract"]),
        ("test_x_contour.py", ["affected_contour"]),
    ):
        (unit / name).write_text(
            "from app.x import helper\n\ndef test_ok():\n    assert helper() == 1\n",
            encoding="utf-8",
        )
        (unit / name.replace(".py", ".opsx-roles.json")).write_text(
            json.dumps(
                {
                    "schema": "opsx-resolve-conflict/test-roles/v1",
                    "roles": roles,
                    "covers_paths": ["app/x.py"],
                    "covers_symbols": ["helper"],
                }
            ),
            encoding="utf-8",
        )
    compiler = FrozenTestPlanCompiler(
        run_id="run-1",
        fingerprint="fingerprint-1",
        scope_sha256="0" * 64,
        content_fingerprints={"app/x.py": "abc"},
        registry_path=registry,
        frozen_contract_hashes=hashes,
        targeted_nodes=("app/x.py",),
        interface_nodes=("tests/unit/test_x_interface.py",),
        contour_nodes=("tests/unit/test_x_contour.py",),
    )
    return compiler.compile()


@pytest.mark.parametrize(
    "argv",
    [
        ["bash", "-c", "git reset --hard"],
        ["sh", "-c", "git push"],
        ["powershell", "-Command", "git rebase --abort"],
        ["python", "-c", "import subprocess; subprocess.run(['git','push'])"],
        ["wrapper.exe", "git", "reset"],
        ["poetry", "run", "python", "-c", "print('x')"],
        ["poetry", "run", "pytest", "tests;git push"],
    ],
)
def test_transitive_shell_or_wrapper_attempts_rejected(frozen_plan, argv: list[str]) -> None:
    with pytest.raises(PolicyViolation):
        assert_frozen_argv(frozen_plan, "pytest-interface", argv)


@pytest.mark.parametrize(
    "argv",
    [
        ["poetry", "run", "pytest", "tests/unit/test_x_interface.py"],
    ],
)
def test_only_frozen_validation_commands_allowed(frozen_plan, argv: list[str]) -> None:
    frozen = assert_frozen_argv(frozen_plan, "pytest-interface", argv)
    assert frozen.argv == tuple(argv)


def test_fast_cannot_disable_full_gate(frozen_plan) -> None:
    with pytest.raises(Exception) as exc:
        effective_final_gate(changed_paths=["app/x.py"], requested_mode="FAST")
    assert "FINAL_FAST_NOT_SUPPORTED" in str(exc.value)
    registry = Path(frozen_plan.payload["registry"])
    root = registry.resolve().parents[2]
    assert effective_final_gate(
        changed_paths=["app/x.py"],
        registry_path=registry,
        requested_mode="FULL",
        frozen_contract_hashes=_hash_static_check_tree(root),
    ) == [
        "WaveA:pyright-strict",
        "WaveA:mypy",
        "WaveA:pytest-unit",
        "WaveB:pytest-full",
    ]


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (
            lambda text: text.replace(
                "checks: [pyright-strict, mypy, pytest-unit]",
                "checks: [pyright-strict, pyright-strict, pytest-unit]",
            ),
            "FULL_VALIDATION_CHECK_DUPLICATE",
        ),
        (
            lambda text: text.replace(
                "checks: [pyright-strict, mypy, pytest-unit]",
                "checks: [pyright-strict, unknown-check, pytest-unit]",
            ),
            "FULL_VALIDATION_CHECK_UNKNOWN",
        ),
    ],
)
def test_invalid_registry_or_descriptor_fails_closed(
    frozen_plan,
    mutation,
    reason: str,
) -> None:
    registry = Path(frozen_plan.payload["registry"])
    registry.write_text(
        mutation(registry.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    root = registry.resolve().parents[2]
    with pytest.raises(Exception) as exc:
        effective_final_gate(
            registry_path=registry,
            requested_mode="FULL",
            frozen_contract_hashes=_hash_static_check_tree(root),
        )
    assert reason in str(exc.value)


def test_missing_pack_file_fails_closed(frozen_plan) -> None:
    registry = Path(frozen_plan.payload["registry"])
    root = registry.resolve().parents[2]
    missing = (
        root / ".cursor" / "static-check" / "checks" / "mypy" / "instructions.md"
    )
    hashes = _hash_static_check_tree(root)
    missing.unlink()
    with pytest.raises(Exception) as exc:
        effective_final_gate(
            registry_path=registry,
            requested_mode="FULL",
            frozen_contract_hashes=hashes,
        )
    assert "FULL_VALIDATION_PACK_FILE_MISSING" in str(exc.value)


def test_pack_bytes_drift_fails_closed(frozen_plan) -> None:
    registry = Path(frozen_plan.payload["registry"])
    root = registry.resolve().parents[2]
    hashes = _hash_static_check_tree(root)
    instructions = (
        root
        / ".cursor"
        / "static-check"
        / "checks"
        / "pytest-full"
        / "instructions.md"
    )
    instructions.write_text(
        instructions.read_text(encoding="utf-8") + "\n# drift\n",
        encoding="utf-8",
    )
    with pytest.raises(Exception) as exc:
        effective_final_gate(
            registry_path=registry,
            requested_mode="FULL",
            frozen_contract_hashes=hashes,
        )
    assert "FULL_VALIDATION_FROZEN_BYTES_MISMATCH" in str(exc.value)


def test_closed_adapter_argv_ignores_pack_markdown(tmp_path: Path) -> None:
    """Pack markdown never becomes argv; closed adapter table wins."""
    registry, hashes = install_actual_registry(tmp_path)
    instructions = (
        tmp_path
        / ".cursor"
        / "static-check"
        / "checks"
        / "pytest-full"
        / "instructions.md"
    )
    instructions.write_text(
        "# pretend argv\npoetry run python -c \"print('nope')\"\n",
        encoding="utf-8",
    )
    hashes[instructions.relative_to(tmp_path).as_posix()] = hashlib.sha256(
        instructions.read_bytes()
    ).hexdigest()
    checks, inventory, _, _ = _load_registry_checks(registry, hashes)
    by_id = {c.check_id: c for c in checks}
    assert list(by_id["pytest-full"].argv) == ["poetry", "run", "pytest"]
    assert "execution.json" not in json.dumps(inventory)
