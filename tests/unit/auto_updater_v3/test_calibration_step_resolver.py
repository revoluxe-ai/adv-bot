"""Unit: adaptive calibration step resolver (×2/÷2)."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
    CalibrationStepState,
    classify_calibration_direct,
    resolve_effective_calibration_steps,
)


@pytest.mark.unit
def test_classify_calibration_direct_loosen_below_ninety_percent() -> None:
    assert classify_calibration_direct(50.0, 100.0) == CalibrationDirect.LOOSEN


@pytest.mark.unit
def test_classify_calibration_direct_tighten_at_ninety_percent() -> None:
    assert classify_calibration_direct(90.0, 100.0) == CalibrationDirect.TIGHTEN


@pytest.mark.unit
def test_resolve_first_tick_always_one() -> None:
    assert (
        resolve_effective_calibration_steps(
            8,
            prev=None,
            current_direct=CalibrationDirect.TIGHTEN,
        )
        == 1
    )


@pytest.mark.unit
def test_resolve_same_direct_doubles_capped() -> None:
    prev = CalibrationStepState(effective_steps=2, direct=CalibrationDirect.TIGHTEN)
    assert (
        resolve_effective_calibration_steps(
            8,
            prev=prev,
            current_direct=CalibrationDirect.TIGHTEN,
        )
        == 4
    )
    prev4 = CalibrationStepState(effective_steps=4, direct=CalibrationDirect.TIGHTEN)
    assert (
        resolve_effective_calibration_steps(
            8,
            prev=prev4,
            current_direct=CalibrationDirect.TIGHTEN,
        )
        == 8
    )
    prev8 = CalibrationStepState(effective_steps=8, direct=CalibrationDirect.TIGHTEN)
    assert (
        resolve_effective_calibration_steps(
            8,
            prev=prev8,
            current_direct=CalibrationDirect.TIGHTEN,
        )
        == 8
    )


@pytest.mark.unit
def test_resolve_flip_direct_halves_floor() -> None:
    prev = CalibrationStepState(effective_steps=8, direct=CalibrationDirect.TIGHTEN)
    assert (
        resolve_effective_calibration_steps(
            8,
            prev=prev,
            current_direct=CalibrationDirect.LOOSEN,
        )
        == 4
    )


@pytest.mark.unit
def test_resolve_loosen_same_direct_multiplies() -> None:
    prev = CalibrationStepState(effective_steps=2, direct=CalibrationDirect.LOOSEN)
    assert (
        resolve_effective_calibration_steps(
            8,
            prev=prev,
            current_direct=CalibrationDirect.LOOSEN,
        )
        == 4
    )


@pytest.mark.unit
def test_resolve_loosen_to_tighten_halves() -> None:
    prev = CalibrationStepState(effective_steps=4, direct=CalibrationDirect.LOOSEN)
    assert (
        resolve_effective_calibration_steps(
            8,
            prev=prev,
            current_direct=CalibrationDirect.TIGHTEN,
        )
        == 2
    )


@pytest.mark.unit
def test_resolve_three_loosen_ticks_double_sequence() -> None:
    """Цепочка LOOSEN: 1 → 2 → 4 при cap=8 (как в production Redis)."""
    steps = 1
    prev = None
    for expected in (1, 2, 4):
        steps = resolve_effective_calibration_steps(
            8,
            prev=prev,
            current_direct=CalibrationDirect.LOOSEN,
        )
        assert steps == expected
        prev = CalibrationStepState(effective_steps=steps, direct=CalibrationDirect.LOOSEN)


@pytest.mark.unit
def test_resolve_halve_never_below_one() -> None:
    prev = CalibrationStepState(effective_steps=1, direct=CalibrationDirect.TIGHTEN)
    assert (
        resolve_effective_calibration_steps(
            8,
            prev=prev,
            current_direct=CalibrationDirect.LOOSEN,
        )
        == 1
    )
