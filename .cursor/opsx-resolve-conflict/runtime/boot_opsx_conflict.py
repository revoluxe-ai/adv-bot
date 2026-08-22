#!/usr/bin/env python3
"""Trusted launcher: disable bytecode **before** importing ``opsx_conflict``.

Prefer ``python -B`` / ``PYTHONDONTWRITEBYTECODE=1`` when invoking the package.
This script sets both flags before the first package import so ``__init__.pyc``
is not written during boot.

R29: uses ``run_cli`` so typed ``StopRequired`` emits a structured STOP envelope
instead of a Python traceback. Unexpected exceptions are not masked.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["OPSX_CONFLICT_BOOTSTRAPPED"] = "1"
sys.dont_write_bytecode = True

_RUNTIME_ROOT = Path(__file__).resolve().parent
if str(_RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(_RUNTIME_ROOT))

from opsx_conflict.runtime import run_cli  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(run_cli())
