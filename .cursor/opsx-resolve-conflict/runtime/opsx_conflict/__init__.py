"""Public package surface for the sealed OPSX conflict runtime.

Bytecode must be disabled before this package is imported (``python -B``,
``PYTHONDONTWRITEBYTECODE=1``, or ``runtime/boot_opsx_conflict.py``). Setting
``sys.dont_write_bytecode`` here is a belt-and-suspenders guard for submodules
loaded after package initialization; it cannot prevent ``__init__.pyc`` when
the interpreter already decided to write bytecode for this module.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True
