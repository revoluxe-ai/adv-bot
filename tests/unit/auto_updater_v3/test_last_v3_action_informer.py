"""Unit-тесты форматирования последнего V3-действия (MSK)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.client_bot.user_interface.views.messages.last_v3_action_informer import (
    format_last_v3_action_str,
    format_snapshot_time_msk,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.last_action_redis import (
    LastV3UpdaterActionSnapshot,
)


@pytest.mark.unit
def test_format_none_is_no_data() -> None:
    assert format_last_v3_action_str(None) == "Нет данных"


@pytest.mark.unit
def test_format_utc_to_msk() -> None:
    ts = datetime(2026, 5, 26, 15, 0, 0, tzinfo=timezone.utc)
    assert format_snapshot_time_msk(ts) == "18:00:00 26-05-2026"


@pytest.mark.unit
def test_format_naive_as_utc_then_msk() -> None:
    ts = datetime(2026, 5, 26, 15, 0, 0)
    assert format_snapshot_time_msk(ts) == "18:00:00 26-05-2026"


@pytest.mark.unit
def test_format_full_line_with_batch() -> None:
    snap = LastV3UpdaterActionSnapshot(
        updated_at=datetime(2026, 5, 26, 15, 32, 6, tzinfo=timezone.utc),
        action=V3ActionType.UP,
        keyword_text="футболка синяя",
        keyword_setting_id=1,
        from_mode="MIN_CPA",
        to_mode="OPTIMUM",
        reason="up_cost_first",
        batch_extra_count=4,
    )
    line = format_last_v3_action_str(snap)
    assert line.startswith("UP «футболка синяя» MIN_CPA→OPTIMUM 18:32:06 26-05-2026")
    assert "(+4 ещё)" in line
    assert "(up_cost_first)" in line


@pytest.mark.unit
def test_format_full_line_with_cycle_aggregate() -> None:
    snap = LastV3UpdaterActionSnapshot(
        updated_at=datetime(2026, 5, 26, 15, 32, 6, tzinfo=timezone.utc),
        action=V3ActionType.DOWN,
        keyword_text="футболка синяя",
        keyword_setting_id=1,
        from_mode="OPTIMUM",
        to_mode="MIN_CPA",
        reason="m2_rebalance_down",
        cycle_aggregate={"up": 3, "down": 2, "force_off": 1},
    )
    line = format_last_v3_action_str(snap)
    assert line.startswith(
        "+3↑ -2↓ off:1 DOWN «футболка синяя» OPTIMUM→MIN_CPA 18:32:06 26-05-2026"
    )
