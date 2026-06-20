"""Unit: side-effects V3 Raise MAX при уменьшении max CPO."""

from __future__ import annotations

import pytest

from app.modules.sales_plan_settings.v3_raise_max_cpo import (
    format_v3_raise_max_auto_disable_message,
    resolve_flag_after_max_cpo_decrease,
)


@pytest.mark.unit
def test_resolve_flag_unchanged_when_flag_off() -> None:
    new_flag, effect = resolve_flag_after_max_cpo_decrease(
        old_max=200,
        new_max=100,
        current_flag=False,
        adv_id=42,
    )
    assert new_flag is False
    assert effect is None


@pytest.mark.unit
def test_resolve_flag_unchanged_when_max_not_decreased() -> None:
    new_flag, effect = resolve_flag_after_max_cpo_decrease(
        old_max=100,
        new_max=150,
        current_flag=True,
        adv_id=42,
    )
    assert new_flag is True
    assert effect is None


@pytest.mark.unit
def test_resolve_flag_disabled_on_max_decrease() -> None:
    new_flag, effect = resolve_flag_after_max_cpo_decrease(
        old_max=200,
        new_max=150,
        current_flag=True,
        adv_id=99,
    )
    assert new_flag is False
    assert effect is not None
    assert effect.adv_id == 99
    assert effect.old_max == 200
    assert effect.new_max == 150


@pytest.mark.unit
def test_format_auto_disable_message() -> None:
    _, effect = resolve_flag_after_max_cpo_decrease(
        old_max=200,
        new_max=150,
        current_flag=True,
        adv_id=99,
    )
    assert effect is not None
    text = format_v3_raise_max_auto_disable_message(effect)
    assert "отключено" in text
    assert "200" in text
    assert "150" in text
    assert "99" in text
