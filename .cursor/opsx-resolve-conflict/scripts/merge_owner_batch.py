"""One-shot Owner merge resolutions for active 55-path merge. Execution only."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def git(*args: str, input_text: str | None = None) -> str:
    r = subprocess.run(
        ["git", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        input=input_text,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"git {args}: {r.stderr or r.stdout}")
    return (r.stdout or "").strip()


def stage_text(path: str, stage: int) -> str | None:
    try:
        return git("show", f":{stage}:{path}")
    except RuntimeError:
        return None


def write_and_add(path: str, content: str) -> None:
    target = REPO / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")
    git("add", "--", path)


def merge_ndjson(path: str, key_field: str = "command_id") -> None:
    ours = stage_text(path, 2) or ""
    theirs = stage_text(path, 3) or ""
    alt_key = "event_id" if "provenance" in path else key_field

    def load_lines(text: str) -> list[dict]:
        out: list[dict] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            out.append(json.loads(line))
        return out

    ours_recs = load_lines(ours)
    theirs_recs = load_lines(theirs)
    ours_keys = {
        str(r.get(key_field) or r.get(alt_key) or r.get("id"))
        for r in ours_recs
    }
    merged = list(ours_recs)
    for rec in theirs_recs:
        ident = str(rec.get(key_field) or rec.get(alt_key) or rec.get("id"))
        if ident not in ours_keys:
            merged.append(rec)
            ours_keys.add(ident)
    content = "\n".join(json.dumps(r, ensure_ascii=True) for r in merged) + "\n"
    write_and_add(path, content)


def target_path(path: str) -> None:
    content = stage_text(path, 2)
    if content is None:
        raise RuntimeError(f"no stage2 for {path}")
    write_and_add(path, content)


def main() -> int:
    # TARGET (stage 2 = current HEAD / target branch)
    for p in [
        "DOTO/WORKLOG.md",
        "conftest.py",
        "app/db/control_acquire.py",
        "app/db/manifest.py",
        "app/db/migrate.py",
        "app/db/provenance.py",
        "tests/docker-compose.test.yml",
    ]:
        print(f"TARGET {p}")
        target_path(p)

  # Registry synthesis
    for p in [
        ".opsx/registry/command_activation.ndjson",
        ".opsx/registry/provenance.ndjson",
    ]:
        print(f"NDJSON {p}")
        merge_ndjson(p)

    print("DONE batch 1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
