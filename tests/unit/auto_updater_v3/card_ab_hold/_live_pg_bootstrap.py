"""Deprecated path: live PG bootstrap перенесён в integration.

Импорт из ``tests.unit..._live_pg_bootstrap`` запрещён — используйте
``tests.integration.card_ab_hold._live_pg_bootstrap``.
"""

from __future__ import annotations

raise ImportError(
    "tests.unit.auto_updater_v3.card_ab_hold._live_pg_bootstrap moved to "
    "tests.integration.card_ab_hold._live_pg_bootstrap "
    "(live PG tests must not live under tests/unit or receive marker fast)"
)
