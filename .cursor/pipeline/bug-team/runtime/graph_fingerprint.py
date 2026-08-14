# -*- coding: utf-8 -*-
"""Reproducible GRAPH inventory fingerprint (BF-008).

EXCLUDE invariant: any opsx-*.md under .cursor/commands that is intentionally
outside ALL_NON_ADMIN inventory (packaged/candidate, admin-adjacent, infra)
MUST be listed in EXCLUDE in the same change as the file land — otherwise
recompute META/GRAPH/INVENTORY via write_inventory/reproduce. Never stamp META
with a reproduce() claim while EXCLUDE lags (attestation becomes false).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

COMMANDS_DIR = Path(".cursor/commands")
EXCLUDE = {
    "opsx-admin-command-analyze-pipeline.md",
    "opsx-admin-command-commit.md",
    "opsx-admin-command-consult.md",
    "opsx-admin-command-design-command.md",
    "opsx-admin-command-fix-command-defects.md",
    "opsx-admin-command-promote-process-lesson.md",
    "opsx-admin-command-resolve-conflicts.md",
    "opsx-execution-preflight.md",
    "opsx-source-resolution.md",
    "opsx-pipeline.md",
    # Packaged candidate (OPSX_RESOLVE_CONFLICT_COMMAND_001); not in ALL_NON_ADMIN graph.
    "opsx-resolve-conflict.md",
}
FINGERPRINT_ALGORITHM = "md5"
FINGERPRINT_INPUT_MODE = "names_only_newline_joined"


def inventory_names() -> List[str]:
    """Return sorted opsx-*.md names minus EXCLUDE."""
    names = sorted(
        p.name for p in COMMANDS_DIR.glob("opsx-*.md") if p.name not in EXCLUDE
    )
    return names


def fingerprint(names: List[str] | None = None) -> str:
    """MD5 of newline-joined inventory names (names_only_newline_joined)."""
    names = names if names is not None else inventory_names()
    return hashlib.md5("\n".join(names).encode("utf-8")).hexdigest()


def write_inventory(path: Path) -> Dict[str, Any]:
    """Write INVENTORY.json from live inventory_names() (mutates path)."""
    names = inventory_names()
    fp = fingerprint(names)
    payload = {
        "FINGERPRINT_ALGORITHM": FINGERPRINT_ALGORITHM,
        "FINGERPRINT_INPUT_MODE": FINGERPRINT_INPUT_MODE,
        "INVENTORY_COUNT": len(names),
        "GRAPH_NODE_COUNT": len(names),
        "NAMES": names,
        "FINGERPRINT": fp,
        "REPRODUCTION_COMMAND": (
            "python -c \"from pathlib import Path; import hashlib; "
            "ex={...}; names=sorted(p.name for p in Path('.cursor/commands').glob('opsx-*.md') "
            "if p.name not in ex); print(len(names), hashlib.md5(chr(10).join(names).encode()).hexdigest())\""
        ),
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    payload["INVENTORY_PATH"] = str(path)
    payload["INVENTORY_CONTENT_SHA256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    # rewrite with hash
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def reproduce() -> Tuple[int, str]:
    """Return (count, fingerprint) from live inventory_names()."""
    names = inventory_names()
    return len(names), fingerprint(names)


def check_attested_inventory(path: Path) -> Tuple[bool, Dict[str, Any]]:
    """Read-only coherence check: attested INVENTORY.json vs live reproduce().

    Loads path without rewriting. Compares INVENTORY_COUNT and FINGERPRINT to
    live reproduce(). Use this (not write_inventory-then-compare) so EXCLUDE
    drift cannot be masked by regeneration.

    Args:
        path: Path to attested INVENTORY.json.

    Returns:
        (ok, detail) where detail always includes attested/live count and
        fingerprint; on mismatch also includes reason.
    """
    live_count, live_fp = reproduce()
    detail: Dict[str, Any] = {
        "path": str(path),
        "live_count": live_count,
        "live_fingerprint": live_fp,
    }
    if not path.is_file():
        detail["ok"] = False
        detail["reason"] = "attested_inventory_missing"
        return False, detail
    payload = json.loads(path.read_text(encoding="utf-8"))
    attested_count = int(payload.get("INVENTORY_COUNT", -1))
    attested_fp = str(payload.get("FINGERPRINT", ""))
    detail["attested_count"] = attested_count
    detail["attested_fingerprint"] = attested_fp
    ok = attested_count == live_count and attested_fp == live_fp
    detail["ok"] = ok
    if not ok:
        detail["reason"] = "attested_inventory_mismatch"
    return ok, detail
