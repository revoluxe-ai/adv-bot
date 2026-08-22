"""R28: actual OPSX registry task_type+pack + closed typed adapters."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

import pytest

from opsx_conflict.errors import StopRequired
from opsx_conflict.validation import (
    EXPECTED_CHECK_ARGV,
    TYPED_CHECK_ADAPTERS,
    VALIDATION_ADAPTER_SCHEMA,
    _load_registry_checks,
    effective_final_gate,
)
from validation_registry_helpers import (
    ACTUAL_FULL_REGISTRY,
    install_actual_registry,
    write_pack_tree,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _actual_registry_and_root() -> tuple[Path, Path]:
    """Resolve supplied registry from host_contracts (package) or live repo.

    Clean-unpack archives nest the package under
    ``candidate/.cursor/opsx-resolve-conflict/`` while ``context/host_contracts``
    remains at the archive root.
    """
    candidates = (
        PACKAGE_ROOT
        / "context"
        / "host_contracts"
        / ".cursor"
        / "static-check"
        / "registry.yaml",
        PACKAGE_ROOT.parents[2]
        / "context"
        / "host_contracts"
        / ".cursor"
        / "static-check"
        / "registry.yaml",
        REPO_ROOT / ".cursor" / "static-check" / "registry.yaml",
    )
    for registry in candidates:
        if registry.is_file():
            return registry, registry.resolve().parents[2]
    raise AssertionError(
        "actual OPSX registry not found; tried: "
        + ", ".join(str(path) for path in candidates)
    )


def test_compile_actual_supplied_registry() -> None:
    """Host registry.yaml compiles without synthetic execution fields."""
    registry, root = _actual_registry_and_root()
    text = registry.read_text(encoding="utf-8")
    assert "task_type:" in text
    assert "pack:" in text
    assert "execution:" not in text
    hashes = {
        registry.relative_to(root).as_posix(): _sha(registry),
    }
    for check_id in ("pyright-strict", "mypy", "pytest-unit", "pytest-full"):
        pack = root / ".cursor" / "static-check" / "checks" / check_id
        for name in ("context.md", "instructions.md"):
            path = pack / name
            hashes[path.relative_to(root).as_posix()] = _sha(path)
    checks, inventory, registry_sha, unclassified = _load_registry_checks(
        registry, hashes
    )
    assert unclassified == ()
    assert registry_sha == hashes[".cursor/static-check/registry.yaml"]
    assert [f"Wave{c.wave}:{c.check_id}" for c in checks] == [
        "WaveA:pyright-strict",
        "WaveA:mypy",
        "WaveA:pytest-unit",
        "WaveB:pytest-full",
    ]
    for check in checks:
        assert tuple(check.argv) == EXPECTED_CHECK_ARGV[check.check_id]
        assert check.adapter_schema == VALIDATION_ADAPTER_SCHEMA
        assert check.pack_inventory_digest
        assert check.pack in inventory


def test_exact_typed_argv_from_adapter_table(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    checks, _, _, _ = _load_registry_checks(registry, hashes)
    by_id = {c.check_id: c for c in checks}
    assert by_id["pyright-strict"].argv == ("poetry", "run", "pyright-strict")
    assert by_id["mypy"].argv == ("poetry", "run", "mypy", ".")
    assert by_id["pytest-unit"].argv == ("poetry", "run", "pytest", "-m", "unit")
    assert by_id["pytest-full"].argv == ("poetry", "run", "pytest")


def test_missing_task_type_stops(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    text = ACTUAL_FULL_REGISTRY.replace(
        "  pyright-strict:\n    task_type: shell\n    pack:",
        "  pyright-strict:\n    pack:",
        1,
    )
    registry.write_text(text, encoding="utf-8")
    hashes[registry.relative_to(tmp_path).as_posix()] = _sha(registry)
    with pytest.raises(StopRequired) as exc:
        _load_registry_checks(registry, hashes)
    assert exc.value.reason == "FULL_VALIDATION_TASK_TYPE_MISSING"


def test_unsupported_task_type_stops(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    text = ACTUAL_FULL_REGISTRY.replace(
        "  mypy:\n    task_type: shell\n",
        "  mypy:\n    task_type: agent\n",
        1,
    )
    registry.write_text(text, encoding="utf-8")
    hashes[registry.relative_to(tmp_path).as_posix()] = _sha(registry)
    with pytest.raises(StopRequired) as exc:
        _load_registry_checks(registry, hashes)
    assert exc.value.reason == "FULL_VALIDATION_ADAPTER_UNAVAILABLE"
    assert exc.value.details.get("task_type") == "agent"


def test_missing_pack_field_stops(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    text = ACTUAL_FULL_REGISTRY.replace(
        "  pytest-unit:\n    task_type: shell\n    pack: .cursor/static-check/checks/pytest-unit\n",
        "  pytest-unit:\n    task_type: shell\n",
        1,
    )
    registry.write_text(text, encoding="utf-8")
    hashes[registry.relative_to(tmp_path).as_posix()] = _sha(registry)
    with pytest.raises(StopRequired) as exc:
        _load_registry_checks(registry, hashes)
    assert exc.value.reason == "FULL_VALIDATION_PACK_MISSING"


def test_wrong_pack_path_stops(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    text = ACTUAL_FULL_REGISTRY.replace(
        "pack: .cursor/static-check/checks/mypy",
        "pack: .cursor/static-check/checks/other-mypy",
        1,
    )
    registry.write_text(text, encoding="utf-8")
    hashes[registry.relative_to(tmp_path).as_posix()] = _sha(registry)
    with pytest.raises(StopRequired) as exc:
        _load_registry_checks(registry, hashes)
    assert exc.value.reason == "FULL_VALIDATION_ADAPTER_UNAVAILABLE"


def test_pack_path_escape_stops(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    text = ACTUAL_FULL_REGISTRY.replace(
        "pack: .cursor/static-check/checks/pytest-full",
        "pack: ../outside",
        1,
    )
    registry.write_text(text, encoding="utf-8")
    hashes[registry.relative_to(tmp_path).as_posix()] = _sha(registry)
    with pytest.raises(StopRequired) as exc:
        _load_registry_checks(registry, hashes)
    assert exc.value.reason == "FULL_VALIDATION_PACK_PATH_ESCAPE"


def test_symlink_pack_stops(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    pack = tmp_path / ".cursor" / "static-check" / "checks" / "mypy"
    target = tmp_path / "pack-target"
    # Replace directory with symlink to a copy.
    import shutil

    shutil.copytree(pack, target)
    shutil.rmtree(pack)
    try:
        pack.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")
    with pytest.raises(StopRequired) as exc:
        _load_registry_checks(registry, hashes)
    assert exc.value.reason == "FULL_VALIDATION_PACK_SYMLINK"


def test_missing_pack_directory_stops(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    import shutil

    shutil.rmtree(tmp_path / ".cursor" / "static-check" / "checks" / "pytest-unit")
    with pytest.raises(StopRequired) as exc:
        _load_registry_checks(registry, hashes)
    assert exc.value.reason == "FULL_VALIDATION_PACK_DIRECTORY_MISSING"


def test_extra_pack_file_stops(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    extra = (
        tmp_path
        / ".cursor"
        / "static-check"
        / "checks"
        / "pyright-strict"
        / "execution.json"
    )
    extra.write_text("{}", encoding="utf-8")
    with pytest.raises(StopRequired) as exc:
        _load_registry_checks(registry, hashes)
    assert exc.value.reason == "FULL_VALIDATION_PACK_FILE_EXTRA"


def test_changed_pack_bytes_stops(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    path = (
        tmp_path
        / ".cursor"
        / "static-check"
        / "checks"
        / "pytest-full"
        / "context.md"
    )
    path.write_text(path.read_text(encoding="utf-8") + "x", encoding="utf-8")
    with pytest.raises(StopRequired) as exc:
        _load_registry_checks(registry, hashes)
    assert exc.value.reason == "FULL_VALIDATION_FROZEN_BYTES_MISMATCH"


def test_unknown_check_no_generic_argv(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    text = ACTUAL_FULL_REGISTRY.replace(
        "checks: [pyright-strict, mypy, pytest-unit]",
        "checks: [pyright-strict, mypy, pytest-unit, mystery]",
        1,
    ).replace(
        "  pytest-full:",
        "  mystery:\n    task_type: shell\n"
        "    pack: .cursor/static-check/checks/mystery\n"
        "  pytest-full:",
        1,
    )
    registry.write_text(text, encoding="utf-8")
    hashes[registry.relative_to(tmp_path).as_posix()] = _sha(registry)
    write_pack_tree(tmp_path, "mystery")
    for rel, digest in {
        path.relative_to(tmp_path).as_posix(): _sha(path)
        for path in (
            tmp_path / ".cursor" / "static-check" / "checks" / "mystery"
        ).rglob("*")
        if path.is_file()
    }.items():
        hashes[rel] = digest
    with pytest.raises(StopRequired) as exc:
        _load_registry_checks(registry, hashes)
    assert exc.value.reason == "FULL_VALIDATION_ADAPTER_UNAVAILABLE"
    assert exc.value.details.get("check_id") == "mystery"


def test_registry_digest_drift_stops(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    stale = dict(hashes)
    registry.write_text(registry.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    with pytest.raises(StopRequired) as exc:
        _load_registry_checks(registry, stale)
    assert exc.value.reason == "FULL_VALIDATION_FROZEN_BYTES_MISMATCH"


def test_pytest_full_dependency_enforcement(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    text = ACTUAL_FULL_REGISTRY.replace(
        "        after: [pytest-unit]\n",
        "        after: [missing-dep]\n",
        1,
    )
    registry.write_text(text, encoding="utf-8")
    hashes[registry.relative_to(tmp_path).as_posix()] = _sha(registry)
    with pytest.raises(StopRequired) as exc:
        _load_registry_checks(registry, hashes)
    assert exc.value.reason == "FULL_VALIDATION_DEPENDENCY_INVALID"


def test_no_execution_json_dependency_in_current_contracts() -> None:
    """Current runtime/command paths must not require execution.json."""
    validation = (
        PACKAGE_ROOT / "runtime" / "opsx_conflict" / "validation.py"
    ).read_text(encoding="utf-8")
    command = (
        PACKAGE_ROOT
        / "candidate"
        / ".cursor"
        / "commands"
        / "opsx-resolve-conflict.md"
    ).read_text(encoding="utf-8")
    # Live contract path must not require execution.json (historical markers ok).
    assert "execution.json" not in validation or "HISTORICAL_BASELINE_ALLOWLIST" in validation
    assert "config.get(\"execution\")" not in validation
    assert "checks/pyright-strict/execution.json" not in command
    assert "task_type" in command
    assert "closed" in command.lower() or "typed adapter" in command.lower()


def test_pack_content_never_passed_to_process_execution(tmp_path: Path) -> None:
    """Frozen argv must equal closed adapter table, never pack file text."""
    registry, hashes = install_actual_registry(tmp_path)
    instructions = (
        tmp_path
        / ".cursor"
        / "static-check"
        / "checks"
        / "mypy"
        / "instructions.md"
    )
    instructions.write_text(
        "RUN: poetry run python -c 'import os; os.system(\"echo pwned\")'\n",
        encoding="utf-8",
    )
    hashes[instructions.relative_to(tmp_path).as_posix()] = _sha(instructions)
    checks, _, _, _ = _load_registry_checks(registry, hashes)
    argv = next(c.argv for c in checks if c.check_id == "mypy")
    assert argv == TYPED_CHECK_ADAPTERS[
        ("mypy", "shell", ".cursor/static-check/checks/mypy")
    ].argv
    assert "python" not in argv
    assert "pwned" not in " ".join(argv)


def test_effective_final_gate_exact_plan(tmp_path: Path) -> None:
    registry, hashes = install_actual_registry(tmp_path)
    assert effective_final_gate(
        registry_path=registry,
        requested_mode="FULL",
        frozen_contract_hashes=hashes,
    ) == [
        "WaveA:pyright-strict",
        "WaveA:mypy",
        "WaveA:pytest-unit",
        "WaveB:pytest-full",
    ]
