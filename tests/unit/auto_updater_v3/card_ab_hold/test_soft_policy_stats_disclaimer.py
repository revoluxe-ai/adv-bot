"""Tasks 23.9: soft-policy RU disclaimer on Enable / status screens.

Decision ``card-ab-hold-write-path-ownership`` §17 soft MVP / UX contract §11:
temporary stats gaps → freeze decide; user monitors; forbid «ослабим защиту».
"""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_screens import (
    build_h1_text,
    build_s3_text,
)

_FORBIDDEN_SOFT_POLICY_PHRASE = "ослабим защиту"

_REQUIRED_DISCLAIMER_MARKERS = (
    "Статистика иногда временно недоступна",
    "не меняет состав ключей",
    "продолжается",
)


@pytest.mark.unit
def test_s0_instruction_has_soft_policy_disclaimer() -> None:
    """S0 Enable instruction MUST carry soft-policy informed-consent copy."""
    text = handlers._INSTRUCTION
    assert handlers.SOFT_POLICY_STATS_DISCLAIMER in text
    for marker in _REQUIRED_DISCLAIMER_MARKERS:
        assert marker in text
    assert _FORBIDDEN_SOFT_POLICY_PHRASE not in text.lower()


@pytest.mark.unit
def test_s3_and_h1_include_soft_policy_line() -> None:
    """In-test status (S3/H1) MUST mention freeze-decide soft policy."""
    s3 = build_s3_text(started_at=None, duration_hours=48)
    h1 = build_h1_text()
    for text in (s3, h1):
        assert "временно недоступна" in text or "устаревает" in text
        assert "не меняет состав ключей" in text
        assert _FORBIDDEN_SOFT_POLICY_PHRASE not in text.lower()
