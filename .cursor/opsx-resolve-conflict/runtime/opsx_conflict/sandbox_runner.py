"""Packaged best-effort validation wrapper — not an OS sandbox.

This runner is allowlisted only as ``enforcement_level=BEST_EFFORT``. It must
never advertise ``network=DENY`` / ``filesystem=SNAPSHOT_ONLY`` as proven
capabilities. GO requires an independently verified OS-level sandbox identity.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


HANDSHAKE_SCHEMA = "opsx-resolve-conflict/sandbox-handshake/v1"
PROTOCOL_ID = "opsx-sandbox-path-confinement/v1"
ENFORCEMENT_LEVEL = "BEST_EFFORT"


def handshake_payload(*, runner_sha256: str) -> dict[str, object]:
    """Return an honest capability handshake (no OS isolation claims)."""
    return {
        "schema": HANDSHAKE_SCHEMA,
        "protocol": PROTOCOL_ID,
        "runner_sha256": runner_sha256,
        "enforcement_level": ENFORCEMENT_LEVEL,
        "network": "UNENFORCED",
        "filesystem": "BEST_EFFORT_CWD",
        "child_processes": "UNENFORCED",
        "enforcement": [
            "cwd_default_snapshot",
            "proxy_env_cleared",
            "unmanaged_shell_name_denied",
        ],
        "limitations": [
            "no_filesystem_namespace",
            "no_network_namespace",
            "no_syscall_sandbox",
            "not_sufficient_for_GO",
        ],
    }


def _run_confined(snapshot: Path, argv: list[str]) -> int:
    if not argv:
        raise SystemExit("SANDBOX_EMPTY_ARGV")
    banned_prefixes = ("cmd", "cmd.exe", "powershell", "powershell.exe", "bash", "sh")
    executable = Path(argv[0]).name.lower()
    if executable in banned_prefixes:
        raise SystemExit(f"SANDBOX_UNMANAGED_SHELL:{executable}")
    env = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONNOUSERSITE": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "http_proxy": "",
        "https_proxy": "",
        "HTTP_PROXY": "",
        "HTTPS_PROXY": "",
        "ALL_PROXY": "",
        "NO_PROXY": "*",
    }
    for key in ("WINDIR", "SYSTEMROOT", "TMP", "TEMP"):
        if key in os.environ:
            env[key] = os.environ[key]
    tmp = snapshot / ".opsx-sandbox-tmp"
    tmp.mkdir(exist_ok=True)
    env["TMP"] = str(tmp)
    env["TEMP"] = str(tmp)
    env["TMPDIR"] = str(tmp)
    completed = subprocess.run(
        argv,
        cwd=str(snapshot),
        env=env,
        check=False,
    )
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for handshake and best-effort check execution."""
    args = list(sys.argv[1:] if argv is None else argv)
    runner_path = Path(__file__).resolve()
    runner_sha256 = hashlib.sha256(runner_path.read_bytes()).hexdigest()
    if args == ["--opsx-handshake"]:
        sys.stdout.write(
            json.dumps(handshake_payload(runner_sha256=runner_sha256), sort_keys=True)
        )
        sys.stdout.write("\n")
        return 0
    if (
        len(args) < 4
        or args[0] != "--network=none"
        or not args[1].startswith("--filesystem-root=")
        or args[2] != "--"
    ):
        raise SystemExit("SANDBOX_ARGV_SHAPE_INVALID")
    snapshot = Path(args[1].split("=", 1)[1]).resolve()
    if not snapshot.is_dir():
        raise SystemExit("SANDBOX_SNAPSHOT_MISSING")
    return _run_confined(snapshot, args[3:])


if __name__ == "__main__":
    raise SystemExit(main())
