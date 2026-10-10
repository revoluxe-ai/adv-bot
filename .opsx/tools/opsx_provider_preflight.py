"""Non-consuming HOME-PC preflight before sealing provider-run packet (no auth)."""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_VENV_LAUNCHERS: tuple[str, ...] = ("python.exe", "pytest.exe", "py.test.exe")


def _check_import(module: str) -> dict[str, Any]:
    try:
        importlib.import_module(module)
        return {"module": module, "status": "OK"}
    except Exception as exc:  # noqa: BLE001 — preflight report
        return {"module": module, "status": "FAIL", "error": str(exc)}


def _check_cmd(cmd: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        ok = result.returncode == 0
        return {
            "cmd": cmd,
            "status": "OK" if ok else "FAIL",
            "returncode": result.returncode,
            "stderr": (result.stderr or "")[:500],
        }
    except FileNotFoundError as exc:
        return {"cmd": cmd, "status": "FAIL", "error": str(exc)}


def _venv_launchers(repo_root: Path) -> list[Path]:
    """Existing ``.venv\\Scripts`` launchers whose integrity label matters on Windows."""

    scripts = repo_root / ".venv" / "Scripts"
    return [scripts / name for name in _VENV_LAUNCHERS if (scripts / name).exists()]


def fix_venv_integrity(repo_root: Path) -> list[dict[str, Any]]:
    """Best-effort raise of ``.venv`` launchers to medium integrity (Windows, untracked).

    Failures are reported as ``WARN`` only: ``icacls`` exits 1299 when the calling
    process token is itself Low (it cannot raise labels), and the authoritative
    verdict is ``check_venv_integrity`` / ``check_process_integrity`` afterwards.
    """

    if sys.platform != "win32":
        return []
    results: list[dict[str, Any]] = []
    failed = False
    for path in _venv_launchers(repo_root):
        attempt = _check_cmd(["icacls", str(path), "/setintegritylevel", "M"])
        attempt["check"] = "fix_integrity_launcher"
        if attempt["status"] != "OK":
            attempt["status"] = "WARN"
            failed = True
        results.append(attempt)
    venv = repo_root / ".venv"
    if failed and venv.exists():
        fallback = _check_cmd(["icacls", str(venv), "/setintegritylevel", "M", "/T"])
        fallback["check"] = "fix_integrity_venv_tree"
        if fallback["status"] != "OK":
            fallback["status"] = "WARN"
        results.append(fallback)
    return results


def check_process_integrity() -> dict[str, Any]:
    """FAIL when this process token is Low integrity (file labels cannot compensate).

    A Low token (sandboxed agent shell) cannot raise labels and Docker Desktop
    denies its named pipe; the cert must be launched from a normal Medium Git Bash.
    """

    if sys.platform != "win32":
        return {"check": "process_integrity", "status": "OK", "note": "not windows"}
    result = subprocess.run(
        ["whoami", "/groups"], capture_output=True, text=True, check=False
    )
    text = (result.stdout or "").lower()
    level = "unknown"
    for name in ("low", "medium", "high", "system"):
        if f"mandatory label\\{name} mandatory level" in text:
            level = name
            if name != "medium":
                break
    return {
        "check": "process_integrity",
        "status": "FAIL" if level == "low" else "OK",
        "process_integrity": level,
        "remedy": (
            "start the cert from a normal (non-sandboxed) Medium-integrity Git Bash; "
            "see .opsx/tools/README.md 'HOME-PC one-time machine fix'"
            if level == "low"
            else ""
        ),
    }


def check_venv_integrity(repo_root: Path) -> dict[str, Any]:
    """FAIL when a venv launcher carries a Low mandatory label.

    Low integrity makes the Docker Desktop named pipe deny the pytest child
    (v5 and v7 provider certification failures).
    """

    if sys.platform != "win32":
        return {"check": "venv_integrity", "status": "OK", "note": "not windows"}
    low: list[str] = []
    for path in _venv_launchers(repo_root):
        result = subprocess.run(
            ["icacls", str(path)], capture_output=True, text=True, check=False
        )
        if "low mandatory level" in (result.stdout or "").lower():
            low.append(str(path))
    return {
        "check": "venv_integrity",
        "status": "FAIL" if low else "OK",
        "low_integrity_launchers": low,
    }


def check_docker_daemon() -> dict[str, Any]:
    """Run ``docker info`` from this interpreter (same integrity as the pytest child)."""

    result = _check_cmd(["docker", "info", "--format", "{{.ServerVersion}}"])
    result["check"] = "docker_daemon_from_venv_python"
    return result


def check_worktree_hygiene(repo_root: Path) -> dict[str, Any]:
    """FAIL on hidden tracked drift or stray compose output that the guard cannot see."""

    problems: list[str] = []
    listing = subprocess.run(
        ["git", "ls-files", "-v"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    for line in (listing.stdout or "").splitlines():
        if line[:1].islower() or line.startswith("S "):
            problems.append(f"hidden_index_flag:{line}")
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if (status.stdout or "").strip():
        problems.append("dirty_worktree")
    if (repo_root / "tests" / "tests").exists():
        problems.append("stray_tests_tests_dir")
    return {
        "check": "worktree_hygiene",
        "status": "FAIL" if problems else "OK",
        "problems": problems[:20],
    }


def run_preflight(
    repo_root: Path,
    *,
    require_docker_daemon: bool = False,
    fix_integrity: bool = False,
) -> dict[str, Any]:
    """Collect import/docker/collect-only checks without AUTHORIZE_ONE_LIVE_RUN.

    Args:
        repo_root: Cert worktree root.
        require_docker_daemon: Also require integrity labels, daemon access and
            worktree hygiene (the checks that would otherwise fail inside the
            one-shot pytest child).
        fix_integrity: Raise ``.venv`` launcher integrity to medium first.
    """

    checks: list[dict[str, Any]] = []
    if fix_integrity:
        checks.extend(fix_venv_integrity(repo_root))
    if require_docker_daemon:
        checks.append(check_process_integrity())
        checks.append(check_venv_integrity(repo_root))
        checks.append(check_docker_daemon())
        checks.append(check_worktree_hygiene(repo_root))
    for mod in ("pytest", "alembic", "sqlalchemy"):
        checks.append(_check_import(mod))

    checks.append(_check_cmd(["docker", "--version"]))
    checks.append(_check_cmd(["docker", "compose", "version"]))
    checks.append(
        _check_cmd(
            [
                "poetry",
                "run",
                "pytest",
                "tests/integration/wb_sky_mcp/",
                "--collect-only",
                "-q",
                "-m",
                "destructive_local",
            ]
        )
    )

    poetry = shutil.which("poetry")
    failed = [c for c in checks if c.get("status") == "FAIL"]
    return {
        "repo_root": str(repo_root),
        "poetry_on_path": poetry is not None,
        "checks": checks,
        "preflight_status": "PASS" if not failed else "FAIL",
        "failed_count": len(failed),
        "note": "Does not consume AUTHORIZE_ONE_LIVE_RUN or run destructive provider tests.",
    }


def main(argv: list[str] | None = None) -> int:
    """CLI: print JSON preflight report; exit 0 only when all checks PASS."""

    parser = argparse.ArgumentParser(description="OPSX provider preflight (non-consuming)")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument(
        "--require-docker-daemon",
        action="store_true",
        help="Fail unless the venv python can reach the Docker daemon and the tree is clean",
    )
    parser.add_argument(
        "--fix-integrity",
        action="store_true",
        help="Windows: set .venv launcher integrity to medium before checking",
    )
    args = parser.parse_args(argv)
    report = run_preflight(
        args.repo.resolve(),
        require_docker_daemon=args.require_docker_daemon,
        fix_integrity=args.fix_integrity,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["preflight_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
