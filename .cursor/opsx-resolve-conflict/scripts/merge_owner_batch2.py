"""Merge batch 2 — synthesis files and fixes."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def git(*args: str) -> str:
    r = subprocess.run(
        ["git", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"git {args}: {r.stderr or r.stdout}")
    return (r.stdout or "").strip()


def stage(path: str, n: int) -> str:
    return git("show", f":{n}:{path}")


def write_add(path: str, content: str) -> None:
    p = REPO / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8", newline="\n")
    git("add", "--", path)


def fix_init() -> None:
    content = '''"""OPSX unified conflict-resolution pipeline runtime (v1 simplified).

Локальный execution kernel для /opsx-resolve-conflict: capture → partition →
classify → resolve → verify. Не является глобальным OPSX lifecycle source of truth.

Public package surface for the sealed OPSX conflict runtime.
Bytecode must be disabled before this package is imported (``python -B``,
``PYTHONDONTWRITEBYTECODE=1``, or ``runtime/boot_opsx_conflict.py``). Setting
``sys.dont_write_bytecode`` here is a belt-and-suspenders guard for submodules
loaded after package initialization; it cannot prevent ``__init__.pyc`` when
the interpreter already decided to write bytecode for this module.
"""

from __future__ import annotations

import os
import sys

__version__ = "1.0.0"

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True
'''
    write_add(
        ".cursor/opsx-resolve-conflict/runtime/opsx_conflict/__init__.py",
        content,
    )


def fix_openspec_index() -> None:
    path = "openspec/decisions/index.md"
    ours = stage(path, 2)
    theirs = stage(path, 3)
    # Union: keep TARGET block before conflict + INCOMING block from theirs
    marker_start = "<<<<<<< HEAD"
    if marker_start in ours:
        ours = ours.split(marker_start)[0].rstrip()
    # extract incoming entries from theirs (between ======= and >>>>>>> if present)
    incoming_block = theirs
    if "=======" in incoming_block:
        incoming_block = incoming_block.split("=======", 1)[1]
    if ">>>>>>>" in incoming_block:
        incoming_block = incoming_block.split(">>>>>>>", 1)[0]
    # If theirs is clean file, take only new decision bullets not in ours
    lines_out = [ours.rstrip(), incoming_block.strip(), ""]
    # Re-append tail after conflict from stage2 if any
    full2 = stage(path, 2)
    if ">>>>>>>" in full2:
        tail = full2.split(">>>>>>>", 1)[1].strip()
        if tail:
            lines_out.append(tail)
    content = "\n".join(lines_out).rstrip() + "\n"
    write_add(path, content)


def synthesis_from_worktree(paths: list[str]) -> None:
    for p in paths:
        git("add", "--", p)
        print(f"staged worktree {p}")


def merge_pyright() -> None:
    path = "pyrightconfig_strict.json"
    ours = json.loads(stage(path, 2))
    theirs = json.loads(stage(path, 3))
    merged = dict(ours)
    for key in ("exclude", "ignore", "reportMissingImports", "reportUnusedCallResult"):
        if key in theirs and key not in merged:
            merged[key] = theirs[key]
        elif key == "exclude" and key in theirs:
            ex = list(merged.get("exclude") or [])
            for item in theirs.get("exclude") or []:
                if item not in ex:
                    ex.append(item)
            merged["exclude"] = ex
    write_add(path, json.dumps(merged, indent=2, ensure_ascii=True) + "\n")


def main() -> None:
    fix_init()
    fix_openspec_index()
    merge_pyright()
    synthesis_from_worktree(
        [
            "app/modules/billing/billing.py",
            "app/client_bot/user_interface/handlers/auto_shelf_bid_control_menu.py",
            "app/modules/shop_menu/message.py",
            "tests/modules/billing/test_billing.py",
            "tests/modules/shop_menu/test_shop_menu_tariff_display.py",
            "tests/unit/test_auto_shelf_bid_control_menu_handler.py",
        ]
    )
    print("batch2 done")


if __name__ == "__main__":
    main()
