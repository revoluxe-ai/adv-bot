# -*- coding: utf-8 -*-
"""Reproducible GRAPH inventory fingerprint (BF-008)."""

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
}
FINGERPRINT_ALGORITHM = "md5"
FINGERPRINT_INPUT_MODE = "names_only_newline_joined"


def inventory_names() -> List[str]:
    names = sorted(
        p.name for p in COMMANDS_DIR.glob("opsx-*.md") if p.name not in EXCLUDE
    )
    return names


def fingerprint(names: List[str] | None = None) -> str:
    names = names if names is not None else inventory_names()
    return hashlib.md5("\n".join(names).encode("utf-8")).hexdigest()


def write_inventory(path: Path) -> Dict[str, Any]:
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
    names = inventory_names()
    return len(names), fingerprint(names)
