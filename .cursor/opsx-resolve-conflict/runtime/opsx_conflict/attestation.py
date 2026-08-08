"""Startup attestation с внешним trust digest для R12 GO.

Digest покрывает executable inventory, canonical security projection
``MANIFEST.json`` (включая ``trusted_sandbox_runners``) и исключает
self-referential hash fields из projection.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from .errors import StopRequired
from .hashutil import sha256_canonical

PACKAGE_VERSION = "0.34.0"
CONTRACT_SCHEMA_VERSION = "opsx-resolve-conflict/v2"
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
PLATFORM_DISPOSITION = "WINDOWS_PREVIEW_ONLY"
# ADR-OPSX-RC-PLATFORM-001 / WINDOWS_PREVIEW_ONLY — Linux/macOS enablement
# requires a separate architecture-change request (git_typed bind ancestry).
SUPPORTED_PLATFORMS = ("windows",)
PLATFORM_DECISION_ID = "ADR-OPSX-RC-PLATFORM-001"
SANDBOX_HANDSHAKE_SCHEMA = "opsx-resolve-conflict/sandbox-handshake/v1"
SANDBOX_PROTOCOL_ID = "opsx-sandbox-path-confinement/v1"
SANDBOX_ENFORCEMENT_OS_VERIFIED = "OS_VERIFIED"
SANDBOX_ENFORCEMENT_BEST_EFFORT = "BEST_EFFORT"


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sandbox_spawn_argv(sandbox_path: Path, *extra: str) -> list[str]:
    """Build an executable argv for a Python or native sandbox runner."""
    if sandbox_path.suffix.lower() == ".py":
        return [sys.executable, str(sandbox_path), *extra]
    return [str(sandbox_path), *extra]


def _run_sandbox_admission_probes(
    sandbox_path: Path,
    *,
    handshake_env: dict[str, str],
) -> dict[str, Any]:
    """Prove claimed OS isolation by executing hostile probes inside the runner."""
    import tempfile

    from .cancellation import run_process

    probe_root = Path(tempfile.mkdtemp(prefix="opsx-sandbox-admit-"))
    snapshot = probe_root / "snapshot"
    outside = probe_root / "outside"
    snapshot.mkdir()
    outside.mkdir()
    marker = outside / "escape.txt"
    host_readable = outside / "host-secret.txt"
    host_readable.write_text("host-secret-material\n", encoding="utf-8")
    probe = snapshot / "probe.py"
    probe.write_text(
        "\n".join(
            [
                "import socket",
                "import subprocess",
                "import sys",
                "from pathlib import Path",
                f"outside = Path(r'''{marker}''')",
                f"host_readable = Path(r'''{host_readable}''')",
                "try:",
                "    outside.write_text('escaped', encoding='utf-8')",
                "    raise SystemExit('SANDBOX_PROBE_FS_ESCAPE')",
                "except OSError:",
                "    pass",
                "try:",
                "    if host_readable.read_text(encoding='utf-8'):",
                "        raise SystemExit('SANDBOX_PROBE_HOST_READ')",
                "except OSError:",
                "    pass",
                "for endpoint in (('1.1.1.1', 80), ('8.8.8.8', 53), ('127.0.0.1', 9)):",
                "    try:",
                "        socket.create_connection(endpoint, timeout=0.5)",
                "        raise SystemExit('SANDBOX_PROBE_NETWORK_ESCAPE')",
                "    except OSError:",
                "        pass",
                "try:",
                "    socket.getaddrinfo('example.invalid', 80)",
                "except OSError:",
                "    pass",
                "else:",
                "    # DNS resolution without OSError implies network/DNS path open.",
                "    raise SystemExit('SANDBOX_PROBE_DNS_ESCAPE')",
                "try:",
                "    subprocess.check_output(",
                "        [sys.executable, '-c', 'print(1)'],",
                "        timeout=2,",
                "    )",
                "    raise SystemExit('SANDBOX_PROBE_CHILD_ESCAPE')",
                "except (OSError, subprocess.SubprocessError):",
                "    pass",
                "raise SystemExit(0)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    argv = _sandbox_spawn_argv(
        sandbox_path,
        "--network=none",
        f"--filesystem-root={snapshot}",
        "--",
        sys.executable,
        str(probe),
    )
    result = run_process(argv, cwd=snapshot, env=handshake_env, timeout=20.0)
    if result.returncode != 0:
        raise StopRequired(
            "SANDBOX_ADMISSION_PROBE_FAILED",
            {
                "returncode": result.returncode,
                "stdout": result.stdout[-1000:],
                "stderr": result.stderr[-1000:],
            },
        )
    if marker.exists():
        raise StopRequired("SANDBOX_ADMISSION_FS_ESCAPE")
    return {
        "filesystem_escape_blocked": True,
        "host_read_blocked": True,
        "network_escape_blocked": True,
        "dns_escape_blocked": True,
        "child_process_escape_blocked": True,
        "probe_exit_code": 0,
    }


def _resolve_sandbox_capability(
    manifest: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any] | None:
    """Admit only allowlisted runners whose enforcement level matches reality.

    GO requires ``enforcement_level=OS_VERIFIED`` in both the package allowlist
    and the runner handshake, plus live admission probes that prove filesystem
    and network escapes are blocked. Best-effort packaged wrappers are never
    enough for GO.
    """
    allowlist = manifest.get("trusted_sandbox_runners")
    if not isinstance(allowlist, list) or not allowlist:
        if mode == "go":
            raise StopRequired("SANDBOX_TRUST_ALLOWLIST_MISSING")
        return None
    trusted: dict[str, dict[str, Any]] = {}
    for entry in allowlist:
        if not isinstance(entry, dict):
            continue
        digest = str(entry.get("sha256", "")).strip().lower()
        protocol = str(entry.get("protocol", "")).strip()
        enforcement = str(entry.get("enforcement_level", "")).strip()
        if (
            len(digest) != 64
            or protocol != SANDBOX_PROTOCOL_ID
            or enforcement
            not in {
                SANDBOX_ENFORCEMENT_OS_VERIFIED,
                SANDBOX_ENFORCEMENT_BEST_EFFORT,
            }
        ):
            raise StopRequired(
                "SANDBOX_TRUST_ALLOWLIST_INVALID",
                {"entry": entry},
            )
        trusted[digest] = entry
    trust_digest = os.environ.get(
        "OPSX_CONFLICT_SANDBOX_TRUST_DIGEST",
        "",
    ).strip().lower()
    if not trust_digest:
        if mode == "go":
            raise StopRequired(
                "VALIDATION_SANDBOX_CAPABILITY_MISSING",
                {"required_env": "OPSX_CONFLICT_SANDBOX_TRUST_DIGEST"},
            )
        return None
    if trust_digest not in trusted:
        raise StopRequired(
            "SANDBOX_TRUST_DIGEST_UNTRUSTED",
            {"digest": trust_digest},
        )
    entry = trusted[trust_digest]
    runner_env = os.environ.get("OPSX_CONFLICT_SANDBOX_RUNNER", "").strip()
    if runner_env:
        sandbox_path = Path(runner_env)
        if not sandbox_path.is_absolute():
            raise StopRequired(
                "VALIDATION_SANDBOX_RUNNER_INVALID",
                {"path": runner_env},
            )
    else:
        package_path = str(
            entry.get("package_path")
            or "runtime/opsx_conflict/sandbox_runner.py"
        )
        sandbox_path = (PACKAGE_ROOT / package_path).resolve()
    if sandbox_path.is_symlink() or not sandbox_path.is_file():
        raise StopRequired(
            "VALIDATION_SANDBOX_RUNNER_INVALID",
            {"path": str(sandbox_path)},
        )
    actual_digest = _file_sha256(sandbox_path)
    if actual_digest != trust_digest:
        raise StopRequired(
            "SANDBOX_RUNNER_DIGEST_MISMATCH",
            {
                "path": str(sandbox_path),
                "expected": trust_digest,
                "actual": actual_digest,
            },
        )
    from .cancellation import run_process

    handshake_env = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONNOUSERSITE": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }
    for key in ("WINDIR", "SYSTEMROOT", "TMP", "TEMP"):
        if key in os.environ:
            handshake_env[key] = os.environ[key]
    result = run_process(
        _sandbox_spawn_argv(sandbox_path, "--opsx-handshake"),
        cwd=sandbox_path.parent,
        env=handshake_env,
        timeout=15.0,
    )
    if result.returncode != 0:
        raise StopRequired(
            "SANDBOX_HANDSHAKE_FAILED",
            {"returncode": result.returncode, "stderr": result.stderr[-1000:]},
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise StopRequired("SANDBOX_HANDSHAKE_INVALID") from exc
    allowlist_level = str(entry.get("enforcement_level", ""))
    handshake_level = str(payload.get("enforcement_level", ""))
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != SANDBOX_HANDSHAKE_SCHEMA
        or payload.get("protocol") != SANDBOX_PROTOCOL_ID
        or payload.get("runner_sha256") != trust_digest
        or handshake_level != allowlist_level
    ):
        raise StopRequired(
            "SANDBOX_HANDSHAKE_CAPABILITY_MISMATCH",
            {"payload": payload, "allowlist_level": allowlist_level},
        )
    if mode == "go":
        if allowlist_level != SANDBOX_ENFORCEMENT_OS_VERIFIED:
            raise StopRequired(
                "STOP_SANDBOX_UNAVAILABLE",
                {
                    "blocker": "BLOCKER_OS_SANDBOX_RUNNER_MISSING",
                    "enforcement_level": allowlist_level,
                    "required": SANDBOX_ENFORCEMENT_OS_VERIFIED,
                    "note": (
                        "Packaged BEST_EFFORT runner is not OS-enforced; "
                        "GO requires an independently supplied OS_VERIFIED runner."
                    ),
                },
            )
        if (
            payload.get("network") != "DENY"
            or payload.get("filesystem") != "SNAPSHOT_ONLY"
            or payload.get("child_processes") != "RUNNER_POLICY"
        ):
            raise StopRequired(
                "SANDBOX_HANDSHAKE_CAPABILITY_MISMATCH",
                {"payload": payload},
            )
        probes = _run_sandbox_admission_probes(
            sandbox_path,
            handshake_env=handshake_env,
        )
    else:
        probes = {"skipped": True, "mode": mode}
    if _file_sha256(sandbox_path) != trust_digest:
        raise StopRequired("SANDBOX_RUNNER_TOCTOU")
    resolved = sandbox_path.resolve()
    spawn_prefix = (
        [sys.executable, str(resolved)]
        if resolved.suffix.lower() == ".py"
        else [str(resolved)]
    )
    return {
        "runner": str(resolved),
        "spawn_argv_prefix": spawn_prefix,
        "sha256": trust_digest,
        "trust_digest": trust_digest,
        "protocol": SANDBOX_PROTOCOL_ID,
        "enforcement_level": allowlist_level,
        "network": payload.get("network"),
        "filesystem": payload.get("filesystem"),
        "child_processes": payload.get("child_processes"),
        "handshake": payload,
        "admission_probes": probes,
    }


def resolve_state_root(explicit: Path | None = None) -> Path:
    """Single durable-state root used by gate, ledger, manifests, snapshots."""
    if explicit is not None:
        return explicit.resolve()
    env = os.environ.get("OPSX_CONFLICT_STATE")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".opsx-resolve-conflict").resolve()


def load_manifest() -> dict[str, Any]:
    path = PACKAGE_ROOT / "MANIFEST.json"
    if not path.exists():
        raise StopRequired("PACKAGE_MANIFEST_MISSING")
    return json.loads(path.read_text(encoding="utf-8"))


def security_manifest_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return canonical security policy without recursive/volatile hash fields."""
    excluded = {
        "package_digest",
        "file_sha256",
        "trust_anchor_sha256",
        "installed_command_sha256",
        "built_at_utc",
    }
    return {key: value for key, value in manifest.items() if key not in excluded}


def security_manifest_sha256(manifest: dict[str, Any]) -> str:
    """Hash the canonical security-relevant manifest projection."""
    raw = json.dumps(
        security_manifest_payload(manifest),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def list_runtime_py_modules() -> list[Path]:
    """All executable Python modules under runtime/opsx_conflict (no __pycache__)."""
    root = PACKAGE_ROOT / "runtime" / "opsx_conflict"
    if not root.is_dir():
        raise StopRequired("RUNTIME_PACKAGE_MISSING")
    files = sorted(
        p for p in root.rglob("*.py") if p.is_file() and "__pycache__" not in p.parts
    )
    return files


def inventory_hashes() -> dict[str, str]:
    """Hash executable inventory plus canonical security manifest policy."""
    out: dict[str, str] = {}
    for p in list_runtime_py_modules():
        rel = p.relative_to(PACKAGE_ROOT).as_posix()
        out[rel] = _file_sha256(p)
    boot = PACKAGE_ROOT / "runtime" / "boot_opsx_conflict.py"
    if boot.is_file():
        out[boot.relative_to(PACKAGE_ROOT).as_posix()] = _file_sha256(boot)
    for rel in (
        "process_surfaces.json",
        "candidate/.cursor/commands/opsx-resolve-conflict.md",
        "schemas/scope-manifest.schema.json",
        "schemas/ledger-record.schema.json",
        "schemas/run-receipt.schema.json",
        "schemas/unit-receipt.schema.json",
        "schemas/authority-declaration.schema.json",
        "TRUST_ANCHOR.json",
    ):
        p = PACKAGE_ROOT / rel
        if p.is_file():
            out[rel] = _file_sha256(p)
    manifest_path = PACKAGE_ROOT / "MANIFEST.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        out["MANIFEST.security.json"] = security_manifest_sha256(manifest)
    return out


def hash_required_repo_contracts(
    repo_root: Path,
    required_paths: list[str],
) -> dict[str, str]:
    """Hash exact regular host contracts without path or symlink ambiguity."""
    root = repo_root.resolve()
    hashes: dict[str, str] = {}
    for raw in required_paths:
        if (
            not isinstance(raw, str)
            or not raw
            or "\\" in raw
            or Path(raw).is_absolute()
            or ".." in Path(raw).parts
        ):
            raise StopRequired(
                "HOST_CONTRACT_PATH_INVALID",
                {"path": raw},
            )
        normalized = Path(raw).as_posix()
        if normalized in hashes:
            raise StopRequired(
                "HOST_CONTRACT_PATH_DUPLICATE",
                {"path": normalized},
            )
        candidate = root / normalized
        cursor = root
        symlinked = False
        for part in Path(normalized).parts:
            cursor = cursor / part
            if cursor.is_symlink():
                symlinked = True
                break
        if symlinked:
            raise StopRequired(
                "HOST_CONTRACT_NOT_REGULAR_FILE",
                {"path": normalized},
            )
        path = candidate.resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise StopRequired(
                "HOST_CONTRACT_PATH_ESCAPE",
                {"path": normalized},
            ) from exc
        if not path.is_file():
            raise StopRequired(
                "HOST_CONTRACT_NOT_REGULAR_FILE",
                {"path": normalized},
            )
        hashes[normalized] = _file_sha256(path)
    return hashes


def assert_repo_contracts_unchanged(
    repo_root: Path,
    expected_hashes: dict[str, str],
) -> str:
    """Rehash frozen host contracts and return their canonical set digest."""
    actual = hash_required_repo_contracts(repo_root, sorted(expected_hashes))
    if actual != expected_hashes:
        changed = sorted(
            path
            for path in set(actual) | set(expected_hashes)
            if actual.get(path) != expected_hashes.get(path)
        )
        raise StopRequired(
            "HOST_CONTRACT_DRIFT",
            {"paths": changed},
        )
    return sha256_canonical(actual)


def package_digest(hashes: dict[str, str]) -> str:
    """Canonical digest over inventory (trust aggregate)."""
    body = [{"path": k, "sha256": hashes[k]} for k in sorted(hashes) if k != "TRUST_ANCHOR.json"]
    raw = json.dumps(body, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def installed_command_hash(repo_root: Path) -> str | None:
    cmd = repo_root.resolve() / ".cursor" / "commands" / "opsx-resolve-conflict.md"
    if not cmd.is_file():
        return None
    return _file_sha256(cmd)


def effective_acl_ok(path: Path, *, create: bool = True) -> bool:
    """Return whether ``path`` is current-user-only; optionally create it."""
    if create:
        path.mkdir(parents=True, exist_ok=True)
    elif not path.is_dir():
        return False
    if os.name != "nt":
        mode = path.stat().st_mode & 0o777
        return mode & 0o077 == 0
    icacls = shutil.which("icacls")
    if not icacls:
        return False
    from .cancellation import run_process

    result = run_process([icacls, str(path)], timeout=30.0)
    if result.returncode != 0:
        return False
    text = result.stdout.lower().replace(" ", "")
    suspicious = (
        "everyone:(f)",
        "everyone:(m)",
        "everyone:(w)",
        "authenticatedusers:(f)",
        "authenticatedusers:(m)",
        "users:(f)",
        "users:(m)",
    )
    return not any(tok in text for tok in suspicious)


def _host_is_windows() -> bool:
    """Return True on native Windows (test seam for platform gate)."""
    return os.name == "nt"


def assert_supported_platform() -> None:
    """Fail closed unless the host OS is ADR-approved (Windows-only).

    ADR-OPSX-RC-PLATFORM-001 / WINDOWS_PREVIEW_ONLY: Linux and macOS are
    explicitly UNSUPPORTED. Does not alter git_typed / validation / trust-store
    architecture; non-Windows hosts never reach those paths via GO/CLI.
    """
    if _host_is_windows():
        return
    raise StopRequired(
        "UNSUPPORTED_PLATFORM",
        {
            "platform": sys.platform,
            "os_name": os.name,
            "supported_platforms": list(SUPPORTED_PLATFORMS),
            "decision_id": PLATFORM_DECISION_ID,
            "disposition": PLATFORM_DISPOSITION,
        },
    )


def package_compatibility_gate(repo_root: Path, *, mode: str) -> dict[str, Any]:
    """Проверить package closure и внешний installer-provided digest."""
    assert_supported_platform()
    manifest = load_manifest()
    if manifest.get("package_version") != PACKAGE_VERSION:
        raise StopRequired("PACKAGE_VERSION_MISMATCH", {"got": manifest.get("package_version")})
    if manifest.get("contract_schema_version") != CONTRACT_SCHEMA_VERSION:
        raise StopRequired("CONTRACT_SCHEMA_MISMATCH")
    if sys.version_info < (3, 11):
        raise StopRequired("PYTHON_VERSION_UNSUPPORTED", {"version": sys.version})
    if not shutil.which("git"):
        raise StopRequired("GIT_NOT_FOUND")
    entrypoints = manifest.get("entrypoints")
    expected_entrypoints = {
        "command": ".cursor/commands/opsx-resolve-conflict.md",
        "bundled_command": "candidate/.cursor/commands/opsx-resolve-conflict.md",
        "runtime": ".cursor/opsx-resolve-conflict/runtime/opsx_conflict/runtime.py",
        "boot": ".cursor/opsx-resolve-conflict/runtime/boot_opsx_conflict.py",
    }
    if not isinstance(entrypoints, dict) or any(
        entrypoints.get(key) != value for key, value in expected_entrypoints.items()
    ):
        raise StopRequired(
            "ENTRYPOINT_POLICY_MISMATCH",
            {"expected": expected_entrypoints, "actual": entrypoints},
        )

    required = manifest.get("required_repo_paths", [])
    if not isinstance(required, list):
        raise StopRequired("HOST_CONTRACT_LIST_INVALID")
    categories = manifest.get("input_categories")
    if not isinstance(categories, dict):
        raise StopRequired("INPUT_CATEGORIES_MISSING")
    package_owned = categories.get("package_owned_required")
    host_frozen = categories.get("host_frozen_contracts")
    runtime_kinds = categories.get("runtime_repository_input_kinds")
    if (
        not isinstance(package_owned, list)
        or not isinstance(host_frozen, list)
        or not isinstance(runtime_kinds, list)
        or not runtime_kinds
        or set(required) != set(package_owned) | set(host_frozen)
        or set(package_owned) & set(host_frozen)
    ):
        raise StopRequired("INPUT_CATEGORY_SET_MISMATCH")
    required_hashes = hash_required_repo_contracts(repo_root, required)
    expected_contract_hashes = manifest.get("host_contract_sha256")
    if not isinstance(expected_contract_hashes, dict):
        raise StopRequired("HOST_CONTRACT_HASHES_MISSING")
    if set(expected_contract_hashes) != set(host_frozen):
        raise StopRequired(
            "HOST_CONTRACT_EXACT_SET_MISMATCH",
            {
                "expected": sorted(host_frozen),
                "actual": sorted(expected_contract_hashes),
            },
        )
    missing_frozen = sorted(set(expected_contract_hashes) - set(required_hashes))
    if missing_frozen:
        raise StopRequired(
            "HOST_CONTRACT_FREEZE_OUTSIDE_REQUIRED_SET",
            {"paths": missing_frozen},
        )
    contract_hashes = {
        path: required_hashes[path] for path in expected_contract_hashes
    }
    if contract_hashes != expected_contract_hashes:
        changed = sorted(
            path
            for path in set(contract_hashes) | set(expected_contract_hashes)
            if contract_hashes.get(path) != expected_contract_hashes.get(path)
        )
        raise StopRequired(
            "HOST_CONTRACT_HASH_MISMATCH",
            {"paths": changed},
        )
    contract_set_digest = sha256_canonical(contract_hashes)

    # Reject unexpected .py under runtime package
    hashes = inventory_hashes()
    expected = dict(manifest.get("file_sha256", {}))
    # Unexpected runtime modules
    for rel in hashes:
        if rel.startswith("runtime/") and rel.endswith(".py") and rel not in expected:
            raise StopRequired("UNEXPECTED_RUNTIME_MODULE", {"path": rel})
    for rel, digest in expected.items():
        if rel in {"TRUST_ANCHOR.json", "MANIFEST.security.json"}:
            continue
        if hashes.get(rel) != digest:
            raise StopRequired("PACKAGE_HASH_MISMATCH", {"path": rel, "expected": digest, "got": hashes.get(rel)})

    # Trust anchor: package_digest includes MANIFEST security policy.
    digest = package_digest(hashes)
    external_digest = os.environ.get("OPSX_CONFLICT_TRUST_DIGEST", "").strip().lower()
    external_trust_verified = bool(external_digest) and external_digest == digest
    if mode == "go":
        if not external_digest:
            raise StopRequired(
                "EXTERNAL_TRUST_ROOT_MISSING",
                {"required_env": "OPSX_CONFLICT_TRUST_DIGEST"},
            )
        if len(external_digest) != 64 or any(
            ch not in "0123456789abcdef" for ch in external_digest
        ):
            raise StopRequired("EXTERNAL_TRUST_ROOT_INVALID")
        if not external_trust_verified:
            raise StopRequired(
                "EXTERNAL_TRUST_ROOT_MISMATCH",
                {"expected": external_digest, "actual": digest},
            )

    anchor_path = PACKAGE_ROOT / "TRUST_ANCHOR.json"
    if not anchor_path.is_file():
        raise StopRequired("TRUST_ANCHOR_MISSING")
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    if anchor.get("package_version") != PACKAGE_VERSION:
        raise StopRequired("TRUST_ANCHOR_VERSION_MISMATCH")
    if anchor.get("package_digest") != digest:
        raise StopRequired(
            "TRUST_ANCHOR_DIGEST_MISMATCH",
            {"expected": anchor.get("package_digest"), "got": digest},
        )
    if manifest.get("package_digest") != digest:
        raise StopRequired("MANIFEST_PACKAGE_DIGEST_MISMATCH")
    actual_anchor_sha256 = _file_sha256(anchor_path)
    if manifest.get("trust_anchor_sha256") != actual_anchor_sha256:
        raise StopRequired(
            "MANIFEST_TRUST_ANCHOR_HASH_MISMATCH",
            {
                "expected": manifest.get("trust_anchor_sha256"),
                "got": actual_anchor_sha256,
            },
        )

    expected_cmd = manifest.get("installed_command_sha256")
    actual_cmd = installed_command_hash(repo_root)
    bundled_cmd = hashes.get("candidate/.cursor/commands/opsx-resolve-conflict.md")
    if expected_cmd:
        if actual_cmd is None:
            raise StopRequired("INSTALLED_COMMAND_MISSING")
        if actual_cmd != expected_cmd:
            raise StopRequired("INSTALLED_COMMAND_HASH_MISMATCH")
    if actual_cmd != bundled_cmd:
        raise StopRequired(
            "INSTALLED_COMMAND_NOT_BOUND_TO_PACKAGE_DIGEST",
            {"installed": actual_cmd, "bundled": bundled_cmd},
        )

    if mode == "go" and manifest.get("go_capability") is not True:
        raise StopRequired(
            "PACKAGE_GO_CAPABILITY_DISABLED",
            {
                "go_capability": manifest.get("go_capability"),
                "status": manifest.get("status"),
            },
        )

    state_dir = resolve_state_root(None)
    sandbox_capability = _resolve_sandbox_capability(manifest, mode=mode)
    if mode == "preview":
        state_exists = state_dir.is_dir()
        acl_ok = (
            effective_acl_ok(state_dir, create=False) if state_exists else True
        )
        caps = {
            "git": True,
            "poetry": shutil.which("poetry") is not None,
            "process_cancellation": True,
            "acl_enforcement": acl_ok,
            "state_root": str(state_dir) if state_exists else None,
            "validation_sandbox": sandbox_capability,
        }
    else:
        caps = {
            "git": True,
            "poetry": shutil.which("poetry") is not None,
            "process_cancellation": True,
            "acl_enforcement": effective_acl_ok(state_dir, create=True),
            "state_root": str(state_dir),
            "validation_sandbox": sandbox_capability,
        }
    if mode == "go" and not caps["acl_enforcement"]:
        raise StopRequired("ACL_CAPABILITY_MISSING", {"state_dir": str(state_dir)})
    if mode == "go" and not caps["poetry"]:
        raise StopRequired("POETRY_CAPABILITY_MISSING")
    if mode == "go" and sandbox_capability is None:
        raise StopRequired("VALIDATION_SANDBOX_CAPABILITY_MISSING")

    return {
        "package_version": PACKAGE_VERSION,
        "contract_schema_version": CONTRACT_SCHEMA_VERSION,
        "hashes": hashes,
        "host_contract_sha256": contract_hashes,
        "host_contract_set_digest": contract_set_digest,
        "package_digest": digest,
        "installed_command_sha256": actual_cmd,
        "state_root": str(state_dir),
        "capabilities": caps,
        "SAFE_TO_USE_PREVIEW": True,
        "external_trust_verified": external_trust_verified,
        "SAFE_TO_USE_GO": (
            caps["acl_enforcement"]
            and caps["poetry"]
            and sandbox_capability is not None
            and external_trust_verified
        ),
    }
