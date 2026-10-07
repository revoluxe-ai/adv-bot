"""Forbidden source guard (S11,S12)."""

from __future__ import annotations

import pytest

from app.modules.ai_package_v1.keyword_performance.guards.forbidden_sources import (
    FORBIDDEN_MODULES,
    assert_forbidden_sources_not_loaded,
)
from tests.unit.ai_package_v1.keyword_performance.conftest import (
    FakeKeywordDeps,
    GENERATED_AT,
    PERIOD,
    SHOP_ID,
    build_fake_assembler,
)

pytestmark = pytest.mark.unit


def test_forbidden_graphic_import() -> None:
    loaded = set(__import__("sys").modules.keys())
    for mod in FORBIDDEN_MODULES:
        assert mod not in loaded


@pytest.mark.asyncio
async def test_forbidden_guard_on_export_path(fake_deps: FakeKeywordDeps) -> None:
    """Export assembler invokes real forbidden-source guard before IO."""
    assembler = build_fake_assembler(fake_deps)
    _ = await assembler.assemble(
        shop_id=SHOP_ID,
        manifest_shop_id="1",
        period=PERIOD,
        generated_at=GENERATED_AT,
    )


def test_forbidden_guard_raises_when_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    sys.modules["app.utils.graphic_positions_creator.graphic_positions_creator"] = object()  # type: ignore[assignment]
    with pytest.raises(RuntimeError, match="forbidden source"):
        assert_forbidden_sources_not_loaded()
    del sys.modules["app.utils.graphic_positions_creator.graphic_positions_creator"]
