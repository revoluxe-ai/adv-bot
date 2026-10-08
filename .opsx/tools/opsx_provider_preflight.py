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


def run_preflight(repo_root: Path) -> dict[str, Any]:
    """Collect import/docker/collect-only checks without AUTHORIZE_ONE_LIVE_RUN."""

    checks: list[dict[str, Any]] = []
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
    failed = [c for c in checks if c.get("status") != "OK"]
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
    args = parser.parse_args(argv)
    report = run_preflight(args.repo.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["preflight_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
