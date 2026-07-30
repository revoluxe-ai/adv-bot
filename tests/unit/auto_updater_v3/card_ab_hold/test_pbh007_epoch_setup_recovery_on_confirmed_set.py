"""PBH-007 RED: post-confirm epoch setup MUST bound recovery_on by confirmed set.

Owner A_PRIME / SAME_INVARIANT as PBH-002
(gates/OWNER_A_B_C_DECISION.json):
- AUTO_ON / recovery_on Allowed only within frozen confirmed set;
- AUTO_ADD / unbounded recovery_on outside confirmed set Forbidden.

Root PBH-002 fixed ``setup_apply`` snapshot_filter + hold_guards seams.
Residual gap (this finding): after keyword confirm, epoch-managed
``process_ab_setup`` calls ``apply_ab_hold_setup_mutations(..., epoch_managed=True)``
WITHOUT ``allowed_phrases_snapshot`` / reading
``card_ab_hold_confirmed_keywords_json`` → ``snapshot_filter is None`` → any
OFF+PASS keyword (including outside confirmed set) may enter ``recovery_on_ids``.

This module encodes the desired call-site + membership contract so pytest
FAILS on current production (RED_CONFIRMED). No production fix here.
Do not weaken by matching the buggy omit-filter behavior.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
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

_SETUP_APPLY = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.setup_apply"
)
_PIPELINES = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.pipelines"
)

_CONFIRMED_PHRASE = "confirmed-kw"
_OUTSIDE_PHRASE = "outside-kw"
_OUTSIDE_KS_ID = 202


def _off_pass_keyword(
    *,
    ks_id: int,
    text: str,
    views: int = 200,
    pfo: float = 80.0,
) -> SimpleNamespace:
    """OFF-latched keyword that classifies PASS (PFO recovered, views>=100)."""
    return SimpleNamespace(
        keyword_setting_original_id=ks_id,
        text=text,
        views=views,
        pay_for_order=pfo,
        position=12.0,
        strategy_mode=KeywordStrategyMode.OFF,
        hard_status=1,
    )


def _stmt_sets_non_off_strategy(stmt: Any) -> bool:
    """True, если Update пишет strategy_mode отличный от OFF (return-ON)."""
    values = getattr(stmt, "_values", None) or {}
    for key, value in values.items():
        key_name = str(getattr(key, "key", None) or getattr(key, "name", None) or key)
        if "strategy_mode" not in key_name:
            continue
        raw = getattr(value, "value", value)
        try:
            if int(raw) != int(KeywordStrategyMode.OFF):
                return True
        except (TypeError, ValueError):
            if raw is not KeywordStrategyMode.OFF and str(raw) not in {
                "0",
                "OFF",
                "KeywordStrategyMode.OFF",
            }:
                return True
    return False


def _return_on_targets(execute_calls: list[Any]) -> set[int]:
    """keyword_setting ids targeted by return-ON (non-OFF strategy) Updates."""
    targets: set[int] = set()
    for call in execute_calls:
        if not call.args:
            continue
        stmt = call.args[0]
        if not _stmt_sets_non_off_strategy(stmt):
            continue
        where = getattr(stmt, "_where_criteria", None) or ()
        for clause in where:
            right = getattr(clause, "right", None)
            value = getattr(right, "value", None)
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    try:
                        targets.add(int(item))
                    except (TypeError, ValueError):
                        pass
            elif value is not None:
                try:
                    targets.add(int(value))
                except (TypeError, ValueError):
                    pass
    return targets


def _post_confirm_adv(
    *,
    confirmed: list[str],
    keywords: list[SimpleNamespace],
) -> SimpleNamespace:
    """Epoch-managed post-confirm campaign (WARM_UP + confirmed_keywords_json)."""
    adv_setting = SimpleNamespace(
        id=20,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_phase=CardAbHoldPhase.WARM_UP.value,
        max_price_for_order=100.0,
        card_ab_hold_confirmed_keywords_json=list(confirmed),
        card_ab_hold_allowed_phrases_snapshot=None,
    )
    return SimpleNamespace(
        adv_id=10,
        shop_id=1,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        adv_setting=adv_setting,
        get_keywords=AsyncMock(return_value=keywords),
        search_adv_id=None,
        nmids=[],
        min_nmids_bids=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pbh007_snapshot_none_recovers_outside_documenting_call_site_obligation() -> None:
    """Document mechanism: snapshot=None → outside OFF+PASS gets return-ON.

    Call-site obligation: omitting allowed_phrases_snapshot after confirm
    makes snapshot_filter None and unbounded recovery_on — why epoch setup
    MUST pass confirmed membership filter.
    """
    outside = _off_pass_keyword(ks_id=_OUTSIDE_KS_ID, text=_OUTSIDE_PHRASE)
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{_SETUP_APPLY}.sm", return_value=mock_cm):
        pass_n, fail_n = await apply_ab_hold_setup_mutations(
            adv_id=10,
            adv_setting_id=20,
            keywords=[outside],  # type: ignore[arg-type]
            max_pay_for_order=100.0,
            allowed_phrases_snapshot=None,
            epoch_managed=True,
        )

    assert pass_n == 1
    assert fail_n == 0
    assert _OUTSIDE_KS_ID in _return_on_targets(mock_session.execute.call_args_list), (
        "Documented risk: apply_ab_hold_setup_mutations(allowed_phrases_snapshot=None) "
        "recovers OFF+PASS keywords outside any confirmed set — epoch call site "
        "MUST supply confirmed filter after keyword confirm"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pbh007_confirmed_snapshot_blocks_outside_recovery_on() -> None:
    """With confirmed snapshot, outside OFF+PASS MUST NOT get return-ON."""
    outside = _off_pass_keyword(ks_id=_OUTSIDE_KS_ID, text=_OUTSIDE_PHRASE)
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{_SETUP_APPLY}.sm", return_value=mock_cm):
        pass_n, fail_n = await apply_ab_hold_setup_mutations(
            adv_id=10,
            adv_setting_id=20,
            keywords=[outside],  # type: ignore[arg-type]
            max_pay_for_order=100.0,
            allowed_phrases_snapshot=[_CONFIRMED_PHRASE],
            epoch_managed=True,
        )

    assert pass_n == 1
    assert fail_n == 0
    assert _OUTSIDE_KS_ID not in _return_on_targets(mock_session.execute.call_args_list), (
        "Owner A_PRIME: recovery_on MUST NOT target keywords outside "
        "allowed_phrases_snapshot / confirmed set"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pbh007_epoch_setup_passes_confirmed_membership_filter() -> None:
    """Post-confirm epoch process_ab_setup MUST pass membership filter into apply.

    Desired: read card_ab_hold_confirmed_keywords_json (or equivalent snapshot)
    and pass as allowed_phrases_snapshot so recovery_on stays within confirmed set.
    Current production omits the kwarg → RED.
    """
    outside = _off_pass_keyword(ks_id=_OUTSIDE_KS_ID, text=_OUTSIDE_PHRASE)
    complex_adv = _post_confirm_adv(
        confirmed=[_CONFIRMED_PHRASE],
        keywords=[outside],
    )
    lock_mgr = MagicMock()
    lock_mgr.acquire = AsyncMock(return_value=True)
    lock_mgr.release = AsyncMock(return_value=None)
    apply_mock = AsyncMock(return_value=(1, 0))

    with (
        patch(
            f"{_PIPELINES}.ensure_search_common_bid_reset_on_enter",
            new_callable=AsyncMock,
        ),
        patch(
            f"{_PIPELINES}.CardAbHoldSignalRedisCache",
            MagicMock(return_value=SimpleNamespace(client=MagicMock())),
        ),
        patch(f"{_PIPELINES}.RedisLockManager", MagicMock(return_value=lock_mgr)),
        patch(f"{_PIPELINES}.apply_ab_hold_setup_mutations", apply_mock),
    ):
        await process_ab_setup(
            complex_adv,  # type: ignore[arg-type]
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=True,
        )

    apply_mock.assert_awaited()
    kwargs = apply_mock.await_args.kwargs
    assert kwargs.get("epoch_managed") is True
    snapshot = kwargs.get("allowed_phrases_snapshot")
    assert snapshot is not None, (
        "PBH-007 / Owner A_PRIME: after keyword confirm, epoch process_ab_setup "
        "MUST pass allowed_phrases_snapshot (from card_ab_hold_confirmed_keywords_json "
        "or equivalent) into apply_ab_hold_setup_mutations; current call omits filter "
        "→ snapshot_filter=None → unbounded recovery_on"
    )
    assert _CONFIRMED_PHRASE in list(snapshot)
    assert _OUTSIDE_PHRASE not in list(snapshot)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pbh007_epoch_setup_must_not_recovery_on_outside_confirmed_set() -> None:
    """Behavioral: post-confirm epoch setup MUST NOT return-ON outside confirmed set.

    Runs real apply_ab_hold_setup_mutations under process_ab_setup; outside
    OFF+PASS keyword must not receive strategy restore when confirmed set
    excludes it. Fails while call site omits membership filter.
    """
    outside = _off_pass_keyword(ks_id=_OUTSIDE_KS_ID, text=_OUTSIDE_PHRASE)
    complex_adv = _post_confirm_adv(
        confirmed=[_CONFIRMED_PHRASE],
        keywords=[outside],
    )
    lock_mgr = MagicMock()
    lock_mgr.acquire = AsyncMock(return_value=True)
    lock_mgr.release = AsyncMock(return_value=None)

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            f"{_PIPELINES}.ensure_search_common_bid_reset_on_enter",
            new_callable=AsyncMock,
        ),
        patch(
            f"{_PIPELINES}.CardAbHoldSignalRedisCache",
            MagicMock(return_value=SimpleNamespace(client=MagicMock())),
        ),
        patch(f"{_PIPELINES}.RedisLockManager", MagicMock(return_value=lock_mgr)),
        patch(f"{_SETUP_APPLY}.sm", return_value=mock_cm),
    ):
        await process_ab_setup(
            complex_adv,  # type: ignore[arg-type]
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=True,
        )

    assert _OUTSIDE_KS_ID not in _return_on_targets(mock_session.execute.call_args_list), (
        "PBH-007 / Owner A_PRIME: post-confirm epoch setup MUST NOT recovery_on "
        f"keyword outside confirmed set (ks_id={_OUTSIDE_KS_ID}, text={_OUTSIDE_PHRASE!r}); "
        "call site must pass confirmed membership filter into apply_ab_hold_setup_mutations"
    )
