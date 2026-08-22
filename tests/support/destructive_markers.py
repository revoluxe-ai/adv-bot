"""Fail-closed marker gate для destructive PG/CH fixtures.

Opt-in env недостаточен: fixture MUST видеть ``@pytest.mark.destructive_local``
на ``request.node`` до Docker / engine / client / DDL.
"""

from __future__ import annotations

from typing import Any

import pytest

DESTRUCTIVE_LOCAL_MARKER: str = "destructive_local"


def has_destructive_local_marker(node: Any) -> bool:
    """True если у item/node есть marker ``destructive_local``."""
    if node is None:
        return False
    if DESTRUCTIVE_LOCAL_MARKER in getattr(node, "keywords", {}):
        return True
    get = getattr(node, "get_closest_marker", None)
    if callable(get):
        return get(DESTRUCTIVE_LOCAL_MARKER) is not None
    return False


def require_destructive_local_marker(request: pytest.FixtureRequest) -> None:
    """Прервать fixture до side effects, если marker отсутствует.

    Raises:
        pytest.fail.Exception: нет ``destructive_local`` на тесте.
    """
    node = request.node
    if has_destructive_local_marker(node):
        return
    pytest.fail(
        f"Fixture {request.fixturename!r} requires @{DESTRUCTIVE_LOCAL_MARKER} "
        "on the test (or module pytestmark). Opt-in env alone is not enough — "
        "refuse Docker/engine/client/DDL.",
        pytrace=False,
    )
