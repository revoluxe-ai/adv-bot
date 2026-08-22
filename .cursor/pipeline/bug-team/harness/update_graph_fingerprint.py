# -*- coding: utf-8 -*-
"""Update GRAPH.md + META.md with reproducible inventory fingerprint (BF-008)."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from graph_fingerprint import FINGERPRINT_ALGORITHM, FINGERPRINT_INPUT_MODE, write_inventory, reproduce

def main() -> None:
    inv = write_inventory(Path(".cursor/pipeline/bug-team/controlled-tests/INVENTORY.json"))
    count, fp = reproduce()
    assert count == inv["INVENTORY_COUNT"] == inv["GRAPH_NODE_COUNT"]
    assert fp == inv["FINGERPRINT"]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    meta = f"""# pipeline graph meta

updated_at_utc: {now}
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: {fp}
fingerprint_strength: names_only
fingerprint_algorithm: {FINGERPRINT_ALGORITHM}
fingerprint_input_mode: {FINGERPRINT_INPUT_MODE}
inventory_count: {count}
source_commit: {head}
approved_by_token: UPDATE GO
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: {inv['INVENTORY_CONTENT_SHA256']}
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  UPDATE GO {now}: Corrective V2 refresh after /opsx-bug-team runtime
  enforcement. Candidate remains NOT_ACTIVE. Inventory {count} nodes;
  fingerprint independently reproduced via graph_fingerprint.reproduce().
"""
    Path(".cursor/pipeline/META.md").write_text(meta, encoding="utf-8")

    graph = Path(".cursor/pipeline/GRAPH.md").read_text(encoding="utf-8")
    # Replace meta block fields if present
    lines = graph.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("- inventory_count:"):
            out.append(f"- inventory_count: {count}")
        elif line.startswith("- fingerprint_strength:"):
            out.append("- fingerprint_strength: names_only")
            out.append(f"- fingerprint_algorithm: {FINGERPRINT_ALGORITHM}")
            out.append(f"- fingerprint_input_mode: {FINGERPRINT_INPUT_MODE}")
        elif line.startswith("- source_commit:"):
            out.append(f"- source_commit: {head}")
        elif line.startswith("- evidence_note:"):
            out.append("- evidence_note: |")
            out.append(
                f"  UPDATE GO {now} Corrective V2: inventory {count}; "
                f"fingerprint {fp} independently reproduced; "
                "Candidate /opsx-bug-team NOT_ACTIVE."
            )
            # skip old evidence_note continuation until next top-level - key
            i += 1
            while i < len(lines) and (
                lines[i].startswith("  ") or lines[i].startswith("\t")
            ):
                i += 1
            continue
        else:
            out.append(line)
        i += 1
    Path(".cursor/pipeline/GRAPH.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("COUNT", count)
    print("FINGERPRINT", fp)
    print("HEAD", head)
    print("MATCH", fp == inv["FINGERPRINT"])


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(".cursor/pipeline/bug-team/runtime").resolve()))
    main()
