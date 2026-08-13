"""Module entrypoint for `python -B -m opsx_conflict`.

Bytecode must already be disabled via ``-B`` / ``PYTHONDONTWRITEBYTECODE`` /
``runtime/boot_opsx_conflict.py``. Setting the flag here is a secondary guard.
"""

from __future__ import annotations

import os
import sys

if not (
    sys.flags.dont_write_bytecode
    or os.environ.get("OPSX_CONFLICT_BOOTSTRAPPED", "").strip() == "1"
):
    raise SystemExit(
        "UNSUPPORTED_ENTRYPOINT_NO_BYTECODE_POLICY: use "
        "`python -B -m opsx_conflict` or `runtime/boot_opsx_conflict.py`"
    )

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

from .runtime import run_cli  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(run_cli())
