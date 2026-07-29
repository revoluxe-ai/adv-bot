"""Unit: fail-closed marker gate для destructive fixtures."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tests.support.destructive_markers import (
    has_destructive_local_marker,
    require_destructive_local_marker,
)


@pytest.mark.unit
def test_has_destructive_local_marker_true() -> None:
    node = SimpleNamespace(
        keywords={"destructive_local": True},
        get_closest_marker=lambda _n: object(),
    )
    assert has_destructive_local_marker(node) is True


@pytest.mark.unit
def test_has_destructive_local_marker_false() -> None:
    node = SimpleNamespace(keywords={}, get_closest_marker=lambda _n: None)
    assert has_destructive_local_marker(node) is False


@pytest.mark.unit
def test_require_destructive_local_marker_fails_without_mark() -> None:
    request = SimpleNamespace(
        fixturename="async_session",
        node=SimpleNamespace(keywords={}, get_closest_marker=lambda _n: None),
    )
    with pytest.raises(pytest.fail.Exception, match="destructive_local"):
        require_destructive_local_marker(request)  # type: ignore[arg-type]
