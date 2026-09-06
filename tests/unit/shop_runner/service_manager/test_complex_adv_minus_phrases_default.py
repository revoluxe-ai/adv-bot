"""Тесты spec stage-landing-readiness для runtime default минус-фраз."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv.complex_adv import (
    ComplexAdv,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("stored_value", "expected"),
    [(None, False), (False, False), (True, True)],
)
def test_auto_update_minus_phrases_does_not_enable_none(
    stored_value: bool | None,
    expected: bool,
) -> None:
    """Spec stage-landing-readiness: ``None`` не включает automation постоянно."""
    complex_adv = ComplexAdv.__new__(ComplexAdv)
    complex_adv._adv_setting = SimpleNamespace(  # type: ignore[attr-defined]
        auto_update_minus_phrases=stored_value
    )

    assert complex_adv.auto_update_minus_phrases is expected


def test_missing_attribute_defaults_to_disabled() -> None:
    """Spec stage-landing-readiness: legacy DTO без поля остаётся выключенным."""
    complex_adv = ComplexAdv.__new__(ComplexAdv)
    complex_adv._adv_setting = SimpleNamespace()  # type: ignore[attr-defined]

    assert complex_adv.auto_update_minus_phrases is False
