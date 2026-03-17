from __future__ import annotations

import datetime
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.shared.domains.wb.exceptions import NotEnoughBalanceOnShopError
from app.modules.auto_budget_manager import (
    AutoBudgetService,
    AutoBudgetEnsureResult,
    AutoBudgetEnsureStatus,
)
from app.shared.domains.wb.enums import (
    AdvType,
)
from app.shared.domains.wb.utils.balance_source import (
    BalanceSnapshot,
    select_balance_source,
    select_balance_source_from_response,
)


@dataclass
class _FakeRedis:
    key: str | None = None
    is_locked: bool = False

    async def set(self, key: str, value: str, ex: int | None = None, nx: bool = False):
        if nx and self.is_locked:
            return False
        self.is_locked = True
        self.key = key
        return True

    async def delete(self, key: str) -> None:
        if key == self.key:
            self.is_locked = False


@dataclass
class _FakeBalanceResponse:
    balance: int
    net: int
    bonus: int


def _build_settings(**overrides):
    base = {
        "AUTO_BUDGET_LOCK_TTL_SEC": 30,
        "AUTO_BUDGET_TOPUP_AMOUNT": 1000,
        "AUTO_BUDGET_MIN_BALANCE": 0,
        "AUTO_BUDGET_MAX_SINGLE_TOPUP_RATIO": 0.5,
        "AUTO_BUDGET_VERIFICATION_ATTEMPTS": 0,
        "AUTO_BUDGET_VERIFICATION_DELAY_SEC": 0.0,
        "UPDATE_FULL_ADV_STAT_PERIOD": 360,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_ensure_budget_skips_when_lock_busy(monkeypatch) -> None:
    fake_redis = _FakeRedis()
    fake_redis.is_locked = True
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    service = AutoBudgetService(redis_client=fake_redis)

    # ensure inner logic is not called when lock busy
    inner = AsyncMock()
    monkeypatch.setattr(service, "_ensure_budget_locked", inner)

    result = await service.ensure_budget(
        adv_setting_id=1,
        campaign_type=AdvType.AUTO,
        wb_manager_hub=MagicMock(),
    )

    assert result.status == AutoBudgetEnsureStatus.LOCK_BUSY
    inner.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_budget_releases_lock(monkeypatch) -> None:
    fake_redis = _FakeRedis()
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    service = AutoBudgetService(redis_client=fake_redis)

    expected = AutoBudgetEnsureResult(
        status=AutoBudgetEnsureStatus.LIMIT_DISABLED,
        campaign_type=AdvType.AUTO,
        adv_id=42,
        spend_today=0.0,
    )
    inner = AsyncMock(return_value=expected)
    monkeypatch.setattr(service, "_ensure_budget_locked", inner)

    result = await service.ensure_budget(
        adv_setting_id=42,
        campaign_type=AdvType.AUTO,
        wb_manager_hub=MagicMock(),
    )

    assert result == expected
    assert fake_redis.is_locked is False
    inner.assert_awaited_once()


def test_compute_planned_amount_always_matches_configured_topup(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(
            AUTO_BUDGET_TOPUP_AMOUNT=1200,
        ),
    )
    wb_modifier = MagicMock()
    wb_modifier.get_campaign_budget = AsyncMock(return_value=MagicMock(total=0))
    wb_modifier.get_campaign_balance = AsyncMock(return_value=MagicMock())
    wb_manager_hub = MagicMock()
    wb_manager_hub.wb_modifier = wb_modifier

    service = AutoBudgetService(redis_client=_FakeRedis())

    # Проверяем, что функция всегда возвращает ровно тот шаг, что задан в настройках.
    planned = service._compute_planned_amount()

    assert planned == 1200


def test_compute_planned_amount_uses_default_topup_amount(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(),
    )
    service = AutoBudgetService(redis_client=_FakeRedis())

    # Без дополнительной конфигурации шаг остаётся прежним (1000).
    planned = service._compute_planned_amount()

    assert planned == 1000


def test_get_campaign_config_selects_search_when_active() -> None:
    adv_setting = SimpleNamespace(
        adv_id=1,
        search_adv_id=200,
        auto_budget_daily_limit=0,
        search_auto_budget_daily_limit=500,
        auto_budget_balance_type="balance",
        search_auto_budget_balance_type="bonus",
    )

    config = AutoBudgetService.get_campaign_config(
        adv_setting,
        AdvType.SEARCH,
    )

    assert config is not None
    assert config.adv_id == 200
    assert config.limit == 500


def test_normalize_balance_type(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    service = AutoBudgetService(redis_client=_FakeRedis())
    assert service._normalize_balance_type("  BONUS ") == "bonus"
    assert service._normalize_balance_type(None) == "balance"


def test_balance_source_prefers_min_sufficient_value() -> None:
    snapshot = BalanceSnapshot(balance=1500, net=1200, bonus=1100)
    balance_type, source = select_balance_source(snapshot)
    assert balance_type == 3
    assert source == "bonus"


def test_balance_source_raises_when_insufficient() -> None:
    snapshot = BalanceSnapshot(balance=500, net=400, bonus=300)
    with pytest.raises(NotEnoughBalanceOnShopError):
        select_balance_source(snapshot)


def test_balance_source_from_response_prefers_min_sufficient_value() -> None:
    response = _FakeBalanceResponse(balance=1500, net=1200, bonus=1100)
    balance_type, source = select_balance_source_from_response(response)
    assert balance_type == 3
    assert source == "bonus"


def test_balance_source_from_response_raises_when_insufficient() -> None:
    response = _FakeBalanceResponse(balance=500, net=400, bonus=300)
    with pytest.raises(NotEnoughBalanceOnShopError):
        select_balance_source_from_response(response)


class _FakeExecutionResult:
    def __init__(self, value: float | SimpleNamespace = 0.0) -> None:
        self._value = value

    def unique(self) -> _FakeExecutionResult:
        return self

    def scalar(self) -> float:
        return self._value  # type: ignore[return-value]

    def scalar_one_or_none(self) -> float | SimpleNamespace | None:
        return self._value


class _FakeAdvSettingSession:
    def __init__(self, adv_setting, execute_values: list[float] | None = None):
        self._adv_setting = adv_setting
        self._execute_values = execute_values or []
        self._execute_call_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def get(self, model, id):
        return self._adv_setting

    async def execute(self, _stmt):
        self._execute_call_count += 1
        # First execute is select(AdvSetting) -> must return adv_setting for unique().scalar_one_or_none()
        if self._execute_call_count == 1:
            return _FakeExecutionResult(self._adv_setting)
        value = self._execute_values.pop(0) if self._execute_values else 0.0
        return _FakeExecutionResult(value)

    def add(self, entry):
        self._latest_entry = entry

    async def commit(self):
        return None

    async def refresh(self, entry):
        return entry


def _patch_adv_setting(monkeypatch, adv_setting, execute_values: list[float] | None = None):
    def _fake_sm(**kwargs):
        return _FakeAdvSettingSession(adv_setting, execute_values=execute_values)

    monkeypatch.setattr("app.modules.auto_budget_manager.service.sm", _fake_sm)


def _build_adv_setting() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        adv_id=42,
        auto_budget_daily_limit=1000,
        auto_budget_balance_type="balance",
        search_adv_id=None,
        search_auto_budget_daily_limit=0,
        search_auto_budget_balance_type=None,
    )


def _build_wb_manager_hub():
    wb_modifier = MagicMock()
    wb_modifier.get_campaign_budget = AsyncMock(return_value=MagicMock(total=0))
    balance_response = SimpleNamespace(balance=2500, net=2500, bonus=2500)
    wb_modifier.get_campaign_balance = AsyncMock(return_value=balance_response)
    wb_manager_hub = MagicMock()
    wb_manager_hub.wb_modifier = wb_modifier
    return wb_manager_hub


@pytest.mark.asyncio
async def test_ensure_budget_limits_by_successful_topups(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    adv_setting = _build_adv_setting()
    _patch_adv_setting(monkeypatch, adv_setting)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_daily_topup_sums",
        AsyncMock(return_value=(adv_setting.auto_budget_daily_limit, 0.0)),
    )

    wb_modifier = SimpleNamespace(
        get_campaign_budget=AsyncMock(
            return_value=SimpleNamespace(total=500, raw={"current": 500})
        ),
        get_campaign_balance=AsyncMock(return_value={"balance": []}),
        top_up_budget=AsyncMock(return_value=SimpleNamespace(total=600, raw={"ok": True})),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.select_balance_source_from_response",
        lambda response: (None, "balance_type"),
    )
    service = AutoBudgetService(redis_client=_FakeRedis())
    wb_manager_hub = _build_wb_manager_hub()
    result = await service._ensure_budget_locked(
        adv_setting_id=adv_setting.id,
        campaign_type=AdvType.AUTO,
        wb_manager_hub=wb_manager_hub,
    )

    assert result.status == AutoBudgetEnsureStatus.LIMIT_REACHED
    assert result.reason == "Daily successful top-ups already reached limit"
    assert result.available_limit == 0


@pytest.mark.asyncio
async def test_ensure_budget_limits_by_doubled_all_attempts(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    adv_setting = _build_adv_setting()
    adv_setting.auto_budget_daily_limit = 300
    _patch_adv_setting(monkeypatch, adv_setting)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_daily_topup_sums",
        AsyncMock(return_value=(0.0, 2000.0)),
    )
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
    monkeypatch.setattr(
        AutoBudgetService,
        "_get_last_full_stat_update",
        AsyncMock(return_value=now),
    )

    wb_modifier = SimpleNamespace(
        get_campaign_budget=AsyncMock(
            return_value=SimpleNamespace(total=500, raw={"current": 500})
        ),
        get_campaign_balance=AsyncMock(return_value={"balance": []}),
        top_up_budget=AsyncMock(return_value=SimpleNamespace(total=600)),
    )
    wb_manager_hub = SimpleNamespace(wb_modifier=wb_modifier)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.select_balance_source_from_response",
        lambda response: (None, "balance_type"),
    )
    service = AutoBudgetService(redis_client=_FakeRedis())
    wb_manager_hub = _build_wb_manager_hub()
    result = await service._ensure_budget_locked(
        adv_setting_id=adv_setting.id,
        campaign_type=AdvType.AUTO,
        wb_manager_hub=wb_manager_hub,
    )

    assert result.status == AutoBudgetEnsureStatus.LIMIT_REACHED
    assert result.reason == "Daily top-up attempts doubled exceed limit"
    assert result.available_limit == 0


@pytest.mark.asyncio
async def test_ensure_common_budget_skips_when_lock_busy(monkeypatch) -> None:
    fake_redis = _FakeRedis()
    fake_redis.is_locked = True
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    service = AutoBudgetService(redis_client=fake_redis)
    inner = AsyncMock()
    monkeypatch.setattr(service, "_ensure_common_budget_locked", inner)

    result = await service.ensure_common_budget(
        adv_setting_id=1,
        wb_manager_hub=MagicMock(),
    )

    assert result is not None
    assert result.status == AutoBudgetEnsureStatus.LOCK_BUSY
    inner.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_common_budget_releases_lock(monkeypatch) -> None:
    fake_redis = _FakeRedis()
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    service = AutoBudgetService(redis_client=fake_redis)
    expected = AutoBudgetEnsureResult(
        status=AutoBudgetEnsureStatus.LIMIT_DISABLED,
        campaign_type=AdvType.AUTO,
        adv_id=42,
        spend_today=0.0,
    )
    inner = AsyncMock(return_value=expected)
    monkeypatch.setattr(service, "_ensure_common_budget_locked", inner)

    result = await service.ensure_common_budget(
        adv_setting_id=1,
        wb_manager_hub=MagicMock(),
    )

    assert result == expected
    assert fake_redis.is_locked is False
    inner.assert_awaited_once()


def _build_common_adv_setting() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        adv_id=42,
        search_adv_id=43,
        use_common_budget=True,
        common_budget_daily_limit=500,
    )


@pytest.mark.asyncio
async def test_ensure_common_budget_locked_limit_reached_when_topups_exceed(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    adv_setting = _build_common_adv_setting()
    _patch_adv_setting(monkeypatch, adv_setting)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_last_full_stat_update",
        AsyncMock(
            return_value=datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=3))
            )
        ),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_daily_topup_sums_common",
        AsyncMock(return_value=(500.0, 0.0)),
    )

    service = AutoBudgetService(redis_client=_FakeRedis())
    result = await service._ensure_common_budget_locked(
        adv_setting_id=adv_setting.id,
        wb_manager_hub=MagicMock(),
    )

    assert result.status == AutoBudgetEnsureStatus.LIMIT_REACHED
    assert result.reason == "Daily successful top-ups already reached limit"
    assert result.available_limit == 0
    assert result.spend_today == 0.0


@pytest.mark.asyncio
async def test_ensure_common_budget_rejects_when_one_campaign_has_stale_stats(
    monkeypatch,
) -> None:
    """When Auto has fresh stats and Search has stale (or vice versa), reject with NOT_NEW_ADV_STATS."""
    period = 600
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(UPDATE_FULL_ADV_STAT_PERIOD=period),
    )
    adv_setting = _build_common_adv_setting()
    _patch_adv_setting(monkeypatch, adv_setting)

    now = datetime.datetime(
        2026, 1, 19, 12, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
    )
    stale = now - datetime.timedelta(seconds=period * 2)

    async def mock_get_last_full(adv_id: int):
        if adv_id == adv_setting.adv_id:
            return now
        return stale

    monkeypatch.setattr(
        AutoBudgetService,
        "_now_msk",
        staticmethod(lambda: now),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_last_full_stat_update",
        AsyncMock(side_effect=mock_get_last_full),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_daily_topup_sums_common",
        AsyncMock(return_value=(0.0, 0.0)),
    )

    service = AutoBudgetService(redis_client=_FakeRedis())
    result = await service._ensure_common_budget_locked(
        adv_setting_id=adv_setting.id,
        wb_manager_hub=MagicMock(),
    )

    assert result.status == AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS
    assert result.reason == "Last full adv stats too old"


@pytest.mark.asyncio
async def test_ensure_common_budget_rejects_when_both_campaigns_have_stale_stats(
    monkeypatch,
) -> None:
    """When both timestamps are stale, reject with NOT_NEW_ADV_STATS."""
    period = 600
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(UPDATE_FULL_ADV_STAT_PERIOD=period),
    )
    adv_setting = _build_common_adv_setting()
    _patch_adv_setting(monkeypatch, adv_setting)

    now = datetime.datetime(
        2026, 1, 19, 12, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
    )
    stale = now - datetime.timedelta(seconds=period * 2)

    monkeypatch.setattr(
        AutoBudgetService,
        "_now_msk",
        staticmethod(lambda: now),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_last_full_stat_update",
        AsyncMock(return_value=stale),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_daily_topup_sums_common",
        AsyncMock(return_value=(0.0, 0.0)),
    )

    service = AutoBudgetService(redis_client=_FakeRedis())
    result = await service._ensure_common_budget_locked(
        adv_setting_id=adv_setting.id,
        wb_manager_hub=MagicMock(),
    )

    assert result.status == AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS
    assert result.reason == "Last full adv stats too old"


@pytest.mark.asyncio
async def test_ensure_common_budget_rejects_when_one_campaign_missing_stats(
    monkeypatch,
) -> None:
    """When either timestamp is None, reject with NOT_NEW_ADV_STATS."""
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(),
    )
    adv_setting = _build_common_adv_setting()
    _patch_adv_setting(monkeypatch, adv_setting)

    now = datetime.datetime(
        2026, 1, 19, 12, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
    )

    async def mock_get_last_full(adv_id: int):
        if adv_id == adv_setting.adv_id:
            return now
        return None

    monkeypatch.setattr(
        AutoBudgetService,
        "_now_msk",
        staticmethod(lambda: now),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_last_full_stat_update",
        AsyncMock(side_effect=mock_get_last_full),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_daily_topup_sums_common",
        AsyncMock(return_value=(0.0, 0.0)),
    )

    service = AutoBudgetService(redis_client=_FakeRedis())
    result = await service._ensure_common_budget_locked(
        adv_setting_id=adv_setting.id,
        wb_manager_hub=MagicMock(),
    )

    assert result.status == AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS
    assert result.reason == "Missing full adv stats for one or both campaigns"


@pytest.mark.asyncio
async def test_ensure_budget_rejects_when_stats_not_refreshed(monkeypatch) -> None:
    period = 600
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(UPDATE_FULL_ADV_STAT_PERIOD=period),
    )
    adv_setting = _build_adv_setting()
    _patch_adv_setting(monkeypatch, adv_setting)

    now = datetime.datetime(
        2026, 1, 19, 12, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
    )
    last_update = now - datetime.timedelta(seconds=period * 2)

    monkeypatch.setattr(
        AutoBudgetService,
        "_now_msk",
        staticmethod(lambda: now),
    )
    monkeypatch.setattr(
        AutoBudgetService,
        "_get_last_full_stat_update",
        AsyncMock(return_value=last_update),
    )

    wb_modifier = SimpleNamespace(
        get_campaign_budget=AsyncMock(
            return_value=SimpleNamespace(total=0, raw={"current": 0})
        ),
        get_campaign_balance=AsyncMock(return_value={"balance": []}),
        top_up_budget=AsyncMock(return_value=SimpleNamespace(total=100, raw={"ok": True})),
    )
    wb_manager_hub = SimpleNamespace(wb_modifier=wb_modifier)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.select_balance_source_from_response",
        lambda response: (None, "balance_type"),
    )
    service = AutoBudgetService(redis_client=_FakeRedis())
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    result = await service._ensure_budget_locked(
        adv_setting_id=adv_setting.id,
        campaign_type=AdvType.AUTO,
        wb_manager_hub=wb_manager_hub,
    )

    assert result.status == AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS
    assert result.reason == "Last Update Full Adv Stats too old"
    assert result.spend_today == 0.0

