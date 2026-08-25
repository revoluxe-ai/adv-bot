"""Apply TARGET-authoritative synthesis to remaining process AI_SEMANTIC paths."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))
from opsx_conflict.authority_policy import synthesize_under_target_authority  # noqa: E402

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
    try:
        return git("show", f":{n}:{path}")
    except RuntimeError:
        return ""


def main() -> None:
    unmerged = git("diff", "--name-only", "--diff-filter=U").splitlines()
    for path in unmerged:
        if not path.strip():
            continue
        ours = stage(path, 2)
        theirs = stage(path, 3)
        if ours == theirs:
            merged = ours
        else:
            merged = synthesize_under_target_authority(ours or "", theirs or "")
        target = REPO / path
        if merged:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(merged, encoding="utf-8", newline="\n")
        elif target.exists():
            target.unlink()
        git("add", "--", path)
        print(f"synthesized {path}")


if __name__ == "__main__":
    main()
