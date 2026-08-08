"""R19 acceptance closures for the independent R18 rejection."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from opsx_conflict.attestation import inventory_hashes, load_manifest
from opsx_conflict.errors import StopRequired
from opsx_conflict.git_typed import TypedGit
from opsx_conflict.validation import FrozenTestPlanCompiler
from validation_registry_helpers import install_actual_registry


def _minimal_registry(root: Path) -> tuple[Path, dict[str, str]]:
    """Install actual FULL registry with pack inventory hashes."""
    return install_actual_registry(root)


def test_local_same_name_symbol_does_not_prove_production_coverage(
    tmp_path: Path,
) -> None:
    """A local homonym function must not satisfy production symbol coverage."""
    registry, hashes = _minimal_registry(tmp_path)
    service = tmp_path / "app" / "service.py"
    service.parent.mkdir(parents=True)
    service.write_text(
        "def feature():\n    raise RuntimeError('broken')\n",
        encoding="utf-8",
    )
    unit = tmp_path / "tests" / "unit"
    unit.mkdir(parents=True)
    (unit / "test_unrelated.py").write_text(
        "from app.service import feature as production_feature\n"
        "\n"
        "def feature():\n"
        "    return True\n"
        "\n"
        "def test_unrelated():\n"
        "    assert feature()\n",
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


def test_monkeypatched_boundary_does_not_prove_symbol_coverage(tmp_path: Path) -> None:
    """Monkeypatching production symbol boundary must invalidate role proof."""
    registry, hashes = _minimal_registry(tmp_path)
    service = tmp_path / "app" / "service.py"
    service.parent.mkdir(parents=True)
    service.write_text("def feature():\n    return 1\n", encoding="utf-8")
    unit = tmp_path / "tests" / "unit"
    unit.mkdir(parents=True)
    (unit / "test_unrelated.py").write_text(
        "from app.service import feature\n"
        "\n"
        "def test_unrelated(monkeypatch):\n"
        "    monkeypatch.setattr('app.service.feature', lambda: True)\n"
        "    assert feature()\n",
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


@pytest.mark.parametrize(
    "assertion",
    [
        "assert (feature(), True)[1]\n",
        "assert feature() or True\n",
        "assert feature() == feature()\n",
    ],
)
def test_unprotected_or_ambiguous_assertions_do_not_prove_coverage(
    tmp_path: Path,
    assertion: str,
) -> None:
    """Coverage requires one protected direct assert call of production symbol."""
    registry, hashes = _minimal_registry(tmp_path)
    service = tmp_path / "app" / "service.py"
    service.parent.mkdir(parents=True)
    service.write_text("def feature():\n    return 1\n", encoding="utf-8")
    unit = tmp_path / "tests" / "unit"
    unit.mkdir(parents=True)
    (unit / "test_unrelated.py").write_text(
        "from app.service import feature\n"
        "\n"
        "def test_unrelated():\n"
        f"    {assertion}",
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


def _write_fake_git(directory: Path, marker: Path) -> Path:
    """Write a fake git executable that marks every invocation."""
    if os.name == "nt":
        script = directory / "git.cmd"
        script.write_text(
            "@echo off\n"
            f"echo called>>\"{marker}\"\n"
            "if \"%1\"==\"--version\" (\n"
            "  echo git version fake\n"
            "  exit /b 0\n"
            ")\n"
            "if \"%1\"==\"rev-parse\" (\n"
            "  echo 0000000000000000000000000000000000000000\n"
            "  exit /b 0\n"
            ")\n"
            "exit /b 0\n",
            encoding="utf-8",
        )
        return script
    script = directory / "git"
    script.write_text(
        "#!/usr/bin/env sh\n"
        f"echo called >> \"{marker}\"\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  echo \"git version fake\"\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"rev-parse\" ]; then\n"
        "  echo \"0000000000000000000000000000000000000000\"\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def test_typed_git_uses_bound_copy_after_source_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing source executable after admission must not change executed bytes."""
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    marker_first = tmp_path / "marker-first.txt"
    marker_second = tmp_path / "marker-second.txt"
    git_path = _write_fake_git(fake_bin, marker_first)
    monkeypatch.setenv(
        "PATH",
        f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
    )
    monkeypatch.setenv(
        "OPSX_CONFLICT_GIT_TRUST_DIGEST",
        hashlib.sha256(git_path.read_bytes()).hexdigest(),
    )
    monkeypatch.delenv("OPSX_CONFLICT_GIT_TRUST_UNBOUND", raising=False)
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(tmp_path / "state"))
    git = TypedGit(tmp_path)
    # Replace source binary after TypedGit admission.
    _write_fake_git(fake_bin, marker_second)
    git.status_porcelain_v2_z()
    assert marker_first.exists()
    assert not marker_second.exists()
    assert Path(git.git_bin).resolve() != git_path.resolve()


def test_boot_launcher_is_in_manifest_trust_closure() -> None:
    """Boot launcher must be hash-bound and declared as entrypoint."""
    manifest = load_manifest()
    hashes = inventory_hashes()
    rel = "runtime/boot_opsx_conflict.py"
    assert manifest["entrypoints"]["boot"].endswith(rel)
    assert rel in hashes
    assert manifest["file_sha256"][rel] == hashes[rel]


def test_startup_without_bootstrap_or_B_is_rejected() -> None:
    """Module startup without no-bytecode policy must fail closed."""
    package_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(package_root / "runtime")
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env.pop("OPSX_CONFLICT_BOOTSTRAPPED", None)
    proc = subprocess.run(
        [sys.executable, "-m", "opsx_conflict", "--version"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    output = f"{proc.stdout}\n{proc.stderr}"
    assert "UNSUPPORTED_ENTRYPOINT_NO_BYTECODE_POLICY" in output

