"""Regression: AdvSetting non-DB runtime flag must stay ClassVar (not mapped).

Protects import/mapping of ``AdvSetting`` when ``_worst_promo_position`` is an
intentional non-mapped runtime flag for property ``worst_promo_position``.

A bare ``bool | None`` class annotation is treated as a mapped attribute under
SQLAlchemy 2 Annotated Declarative and raises ``MappedAnnotationError`` (zlpr),
which blocks models import and ``pytest -m unit`` collection via conftest.

This test uses the already-loaded ORM class (no ``sys.modules.pop`` / reimport):
reimport against sticky MetaData fails with unrelated ``Table already defined``,
not zlpr, and is therefore BAD_TEST setup.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect as sa_inspect

from app.modules.common_slaves.wildberries.models.models import AdvSetting


@pytest.mark.unit
def test_adv_setting_imports_with_worst_promo_runtime_flag() -> None:
    """AdvSetting keeps _worst_promo_position as ClassVar, not a mapped column.

    Would fail if annotation regresses to bare ``bool | None`` (missing ClassVar
    in ``__annotations__``) or if the flag becomes a mapped column/attr.
    """
    assert AdvSetting is not None
    assert hasattr(AdvSetting, "worst_promo_position")

    raw_ann = AdvSetting.__annotations__.get("_worst_promo_position")
    assert raw_ann is not None, "_worst_promo_position must be annotated on AdvSetting"
    # Under from __future__ import annotations this is typically a string.
    assert "ClassVar" in str(raw_ann), (
        "non-mapped runtime flag must use ClassVar[...] "
        f"(got annotation {raw_ann!r}); bare bool|None triggers SA2 zlpr"
    )

    mapper = sa_inspect(AdvSetting)
    mapped_keys = {attr.key for attr in mapper.attrs}
    column_keys = {col.key for col in mapper.columns}
    assert "_worst_promo_position" not in mapped_keys
    assert "_worst_promo_position" not in column_keys
