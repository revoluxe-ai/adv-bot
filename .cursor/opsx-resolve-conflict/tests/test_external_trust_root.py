"""External digest binds runtime and canonical R11 manifest security policy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import opsx_conflict.attestation as attestation
from opsx_conflict.errors import StopRequired


def _write_self_consistent_attacker_package(package: Path, repo: Path) -> str:
    """Create a package whose mutable internal attestations all agree."""
    runtime = package / "runtime" / "opsx_conflict"
    runtime.mkdir(parents=True)
    (runtime / "attacker.py").write_text("SAFE_TO_USE_GO = True\n", encoding="utf-8")
    (package / "runtime" / "boot_opsx_conflict.py").write_text(
        "import sys\nraise SystemExit(0)\n",
        encoding="utf-8",
    )
    bundled = package / "candidate" / ".cursor" / "commands"
    bundled.mkdir(parents=True)
    version = attestation.PACKAGE_VERSION
    command_text = f"---\npackage_version: {version}\n---\n# attacker command\n"
    (bundled / "opsx-resolve-conflict.md").write_text(command_text, encoding="utf-8")
    installed = repo / ".cursor" / "commands"
    installed.mkdir(parents=True)
    (installed / "opsx-resolve-conflict.md").write_text(command_text, encoding="utf-8")

    manifest = {
        "package_version": version,
        "go_capability": True,
        "contract_schema_version": "opsx-resolve-conflict/v2",
        "required_repo_paths": [],
        "host_contract_sha256": {},
        "input_categories": {
            "package_owned_required": [],
            "host_frozen_contracts": [],
            "runtime_repository_input_kinds": ["active Git operation objects"],
        },
        "declared_limitations": ["GO requires independent review"],
        "go_capability": True,
        "trusted_sandbox_runners": [],
        "entrypoints": {
            "command": ".cursor/commands/opsx-resolve-conflict.md",
            "bundled_command": "candidate/.cursor/commands/opsx-resolve-conflict.md",
            "runtime": ".cursor/opsx-resolve-conflict/runtime/opsx_conflict/runtime.py",
            "boot": ".cursor/opsx-resolve-conflict/runtime/boot_opsx_conflict.py",
        },
    }
    manifest_path = package / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    hashes = attestation.inventory_hashes()
    digest = attestation.package_digest(hashes)
    anchor = {
        "schema": "opsx-resolve-conflict/trust-anchor/v1",
        "package_version": version,
        "package_digest": digest,
    }
    anchor_path = package / "TRUST_ANCHOR.json"
    anchor_path.write_text(json.dumps(anchor), encoding="utf-8")
    hashes = attestation.inventory_hashes()
    digest = attestation.package_digest(hashes)
    anchor["package_digest"] = digest
    anchor_path.write_text(json.dumps(anchor), encoding="utf-8")

    manifest["file_sha256"] = {
        path: value
        for path, value in attestation.inventory_hashes().items()
        if path != "TRUST_ANCHOR.json"
    }
    manifest["package_digest"] = digest
    manifest["trust_anchor_sha256"] = attestation._file_sha256(anchor_path)
    manifest["installed_command_sha256"] = attestation._file_sha256(
        installed / "opsx-resolve-conflict.md"
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return digest


def test_coordinated_internal_replacement_fails_external_digest(
    tmp_path: Path, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "attacker-package"
    repo = tmp_path / "repo"
    package.mkdir()
    repo.mkdir()
    monkeypatch.setattr(attestation, "PACKAGE_ROOT", package)
    attacker_digest = _write_self_consistent_attacker_package(package, repo)
    trusted_digest = "1" * 64
    assert attacker_digest != trusted_digest
    monkeypatch.setenv("OPSX_CONFLICT_TRUST_DIGEST", trusted_digest)
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(isolated_state))

    with pytest.raises(StopRequired) as exc:
        attestation.package_compatibility_gate(repo, mode="go")
    assert exc.value.reason == "EXTERNAL_TRUST_ROOT_MISMATCH"


def test_go_requires_external_digest(
    tmp_path: Path, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "package"
    repo = tmp_path / "repo"
    package.mkdir()
    repo.mkdir()
    monkeypatch.setattr(attestation, "PACKAGE_ROOT", package)
    _write_self_consistent_attacker_package(package, repo)
    monkeypatch.delenv("OPSX_CONFLICT_TRUST_DIGEST", raising=False)
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(isolated_state))

    with pytest.raises(StopRequired) as exc:
        attestation.package_compatibility_gate(repo, mode="go")
    assert exc.value.reason == "EXTERNAL_TRUST_ROOT_MISSING"


def test_go_requires_digest_bound_external_sandbox(
    tmp_path: Path,
    isolated_state: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "package"
    repo = tmp_path / "repo"
    package.mkdir()
    repo.mkdir()
    monkeypatch.setattr(attestation, "PACKAGE_ROOT", package)
    trusted_digest = _write_self_consistent_attacker_package(package, repo)
    monkeypatch.setenv("OPSX_CONFLICT_TRUST_DIGEST", trusted_digest)
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(isolated_state))
    monkeypatch.delenv("OPSX_CONFLICT_SANDBOX_RUNNER", raising=False)
    monkeypatch.delenv("OPSX_CONFLICT_SANDBOX_TRUST_DIGEST", raising=False)
    monkeypatch.delenv("OPSX_CONFLICT_SANDBOX_SHA256", raising=False)
    with pytest.raises(StopRequired) as exc:
        attestation.package_compatibility_gate(repo, mode="go")
    assert exc.value.reason in {
        "VALIDATION_SANDBOX_CAPABILITY_MISSING",
        "SANDBOX_TRUST_ALLOWLIST_MISSING",
    }


def test_manifest_policy_mutation_changes_external_digest(
    tmp_path: Path, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "package"
    repo = tmp_path / "repo"
    package.mkdir()
    repo.mkdir()
    monkeypatch.setattr(attestation, "PACKAGE_ROOT", package)
    trusted_digest = _write_self_consistent_attacker_package(package, repo)
    manifest_path = package / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["required_repo_paths"] = []
    manifest["declared_limitations"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    mutated_digest = attestation.package_digest(attestation.inventory_hashes())
    assert mutated_digest != trusted_digest
    monkeypatch.setenv("OPSX_CONFLICT_TRUST_DIGEST", trusted_digest)
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(isolated_state))
    with pytest.raises(StopRequired) as exc:
        attestation.package_compatibility_gate(repo, mode="go")
    assert exc.value.reason == "EXTERNAL_TRUST_ROOT_MISMATCH"


def test_host_contract_drift_and_invalid_paths_fail_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    contract = repo / "contract.md"
    contract.write_text("v1\n", encoding="utf-8")
    frozen = attestation.hash_required_repo_contracts(repo, ["contract.md"])
    contract.write_text("v2\n", encoding="utf-8")
    with pytest.raises(StopRequired) as drift:
        attestation.assert_repo_contracts_unchanged(repo, frozen)
    assert drift.value.reason == "HOST_CONTRACT_DRIFT"

    directory = repo / "not-a-file"
    directory.mkdir()
    with pytest.raises(StopRequired) as non_file:
        attestation.hash_required_repo_contracts(repo, ["not-a-file"])
    assert non_file.value.reason == "HOST_CONTRACT_NOT_REGULAR_FILE"

    with pytest.raises(StopRequired) as escaping:
        attestation.hash_required_repo_contracts(repo, ["../outside.md"])
    assert escaping.value.reason == "HOST_CONTRACT_PATH_INVALID"
