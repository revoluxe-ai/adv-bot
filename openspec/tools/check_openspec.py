"""Run local OpenSpec checks."""

from __future__ import annotations

from collections.abc import Callable

from openspec.tools.check_config_contract import main as check_config_contract


def main() -> int:
    """Run all OpenSpec checks and return a process exit code."""
    checks: list[tuple[str, Callable[[], int]]] = [
        ("config contract", check_config_contract),
    ]

    failed = False

    for name, check in checks:
        print(f"==> OpenSpec {name}")
        result = check()
        if result:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
