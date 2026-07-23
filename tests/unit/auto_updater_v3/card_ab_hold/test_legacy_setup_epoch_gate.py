"""Legacy setup phase-gate: epoch-managed MUST NOT auto-ACTIVE / ENTER TP (§18.4)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.pipelines import (
    process_ab_setup,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_apply import (
    apply_ab_hold_setup_mutations,
)


def _make_keyword(*, ks_id: int, views: int = 200, pfo: float = 50.0, pos: float = 12.0) -> SimpleNamespace:
    return SimpleNamespace(
        keyword_setting_original_id=ks_id,
        text=f"kw-{ks_id}",
        views=views,
        pay_for_order=pfo,
        position=pos,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_ab_setup_skips_when_epoch_managed_phase_set() -> None:
    """§18.4: non-NULL phase → early return, без setup mutations."""
    adv_setting = SimpleNamespace(
        id=1,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_phase=CardAbHoldPhase.WARM_UP.value,
        max_price_for_order=100.0,
    )
    complex_adv = SimpleNamespace(
        adv_id=100,
        shop_id=1,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        adv_setting=adv_setting,
    )
    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.pipelines.apply_ab_hold_setup_mutations",
        new_callable=AsyncMock,
    ) as mock_apply:
        await process_ab_setup(
            complex_adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
        )
    mock_apply.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_ab_hold_setup_mutations_epoch_managed_no_active_or_tp() -> None:
    """§18.4.2: epoch_managed=True — no TP write, no mode→ACTIVE."""
    keywords = [_make_keyword(ks_id=1)]
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_apply.sm",
        return_value=mock_cm,
    ):
        pass_n, fail_n = await apply_ab_hold_setup_mutations(
            adv_id=10,
            adv_setting_id=20,
            keywords=keywords,
            max_pay_for_order=100.0,
            allowed_phrases_snapshot=["kw-1"],
            epoch_managed=True,
        )

    assert pass_n == 1
    assert fail_n == 0
    execute_calls = mock_session.execute.call_args_list
    sql_strings = [str(call.args[0]) for call in execute_calls]
    adv_setting_updates = [
        s for s in sql_strings if "card_ab_hold_mode" in s or "target_place" in s
    ]
    for stmt in adv_setting_updates:
        assert "active" not in stmt.lower() or "card_ab_hold_mode" not in stmt.lower()
    mode_active_updates = [s for s in sql_strings if "card_ab_hold_mode" in s and "active" in s.lower()]
    assert mode_active_updates == []
    tp_updates = [s for s in sql_strings if "target_place" in s]
    assert tp_updates == []
