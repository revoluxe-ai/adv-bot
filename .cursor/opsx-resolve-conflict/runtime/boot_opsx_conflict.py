"""Boot helper: добавляет runtime на sys.path и запускает CLI."""

from __future__ import annotations

import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parent
if str(_RUNTIME) not in sys.path:
    sys.path.insert(0, str(_RUNTIME))

from opsx_conflict.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
