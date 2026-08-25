"""Adversarial tests for R11-CRIT-001 sandbox trust binding."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import opsx_conflict.attestation as attestation
from opsx_conflict.errors import StopRequired


def test_self_attested_hostile_runner_is_rejected(
    tmp_path: Path,
    isolated_state: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Path+self-hash alone must never admit an unlisted runner."""
    package = tmp_path / "package"
    repo = tmp_path / "repo"
    package.mkdir()
    repo.mkdir()
    runtime = package / "runtime" / "opsx_conflict"
    runtime.mkdir(parents=True)
    (runtime / "noop.py").write_text("x = 1\n", encoding="utf-8")
    (package / "runtime" / "boot_opsx_conflict.py").write_text(
        "import sys\nraise SystemExit(0)\n",
        encoding="utf-8",
    )
    hostile = tmp_path / "hostile-runner.py"
    hostile.write_text(
        "#!/usr/bin/env python3\n"
        "import json, hashlib, pathlib, sys\n"
        "p = pathlib.Path(__file__)\n"
        "digest = hashlib.sha256(p.read_bytes()).hexdigest()\n"
        "if sys.argv[1:] == ['--opsx-handshake']:\n"
        "    print(json.dumps({\n"
        "        'schema': 'opsx-resolve-conflict/sandbox-handshake/v1',\n"
        "        'protocol': 'opsx-sandbox-path-confinement/v1',\n"
        "        'runner_sha256': digest,\n"
        "        'network': 'DENY',\n"
        "        'filesystem': 'SNAPSHOT_ONLY',\n"
        "        'child_processes': 'RUNNER_POLICY',\n"
        "    }))\n"
        "    raise SystemExit(0)\n"
        "raise SystemExit(0)\n",
        encoding="utf-8",
    )
    hostile_digest = hashlib.sha256(hostile.read_bytes()).hexdigest()
    packaged = runtime / "sandbox_runner.py"
    packaged.write_text("print('trusted')\n", encoding="utf-8")
    trusted_digest = hashlib.sha256(packaged.read_bytes()).hexdigest()

    monkeypatch.setattr(attestation, "PACKAGE_ROOT", package)
    monkeypatch.setattr(attestation, "PACKAGE_VERSION", "0.20.0")
    command = (
        package / "candidate" / ".cursor" / "commands" / "opsx-resolve-conflict.md"
    )
    command.parent.mkdir(parents=True)
    command.write_text("---\npackage_version: 0.20.0\n---\n", encoding="utf-8")
    installed = repo / ".cursor" / "commands" / "opsx-resolve-conflict.md"
    installed.parent.mkdir(parents=True)
    installed.write_text(command.read_text(encoding="utf-8"), encoding="utf-8")

    manifest = {
        "package_version": "0.20.0",
        "go_capability": True,
        "contract_schema_version": "opsx-resolve-conflict/v2",
        "required_repo_paths": [],
        "host_contract_sha256": {},
        "input_categories": {
            "package_owned_required": [],
            "host_frozen_contracts": [],
            "runtime_repository_input_kinds": ["active Git operation objects"],
        },
        "declared_limitations": [],
        "go_capability": True,
        "trusted_sandbox_runners": [
            {
                "sha256": trusted_digest,
                "protocol": "opsx-sandbox-path-confinement/v1",
                "package_path": "runtime/opsx_conflict/sandbox_runner.py",
                "enforcement_level": "BEST_EFFORT",
            }
        ],
        "entrypoints": {
            "command": ".cursor/commands/opsx-resolve-conflict.md",
            "bundled_command": "candidate/.cursor/commands/opsx-resolve-conflict.md",
            "runtime": ".cursor/opsx-resolve-conflict/runtime/opsx_conflict/runtime.py",
            "boot": ".cursor/opsx-resolve-conflict/runtime/boot_opsx_conflict.py",
        },
    }
    (package / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    hashes = attestation.inventory_hashes()
    digest = attestation.package_digest(hashes)
    anchor = {
        "schema": "opsx-resolve-conflict/trust-anchor/v1",
        "package_version": "0.20.0",
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
    manifest["installed_command_sha256"] = attestation._file_sha256(installed)
    (package / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")

    monkeypatch.setenv("OPSX_CONFLICT_TRUST_DIGEST", digest)
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(isolated_state))
    monkeypatch.setenv("OPSX_CONFLICT_SANDBOX_RUNNER", str(hostile))
    monkeypatch.setenv("OPSX_CONFLICT_SANDBOX_TRUST_DIGEST", hostile_digest)

    with pytest.raises(StopRequired) as exc:
        attestation.package_compatibility_gate(repo, mode="go")
    assert exc.value.reason == "SANDBOX_TRUST_DIGEST_UNTRUSTED"
