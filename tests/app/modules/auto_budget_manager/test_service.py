from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.shared.domains.wb.exceptions import NotEnoughBalanceOnShopError
from app.modules.auto_budget_manager import (
    AutoBudgetService,
    AutoBudgetEnsureResult,
    AutoBudgetEnsureStatus,
)
from app.modules.auto_budget_manager.redis_promo_state_manager import (
    CachedCampaignPromoState,
    CachedShopPromoState,
)
from app.shared.domains.wb.enums import (
    AdvType,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from app.shared.domains.wb.utils.balance_source import (
    BalanceSnapshot,
    CashbackTopup,
    TopUpBalanceDecision,
    cashback_summary_from_response,
    pick_cashback_for_topup,
    select_balance_source,
    select_balance_source_from_response,
    select_topup_balance_decision,
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
    cashbacks: list[dict] | None = None


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


def _wrap_complex_adv(adv_setting: SimpleNamespace) -> SimpleNamespace:
    """Обёртка AdvSetting в контракт ComplexAdv для unit-тестов."""
    return SimpleNamespace(
        adv_setting=adv_setting,
        original_adv_setting_id=adv_setting.id,
        use_common_budget=getattr(adv_setting, "use_common_budget", False),
        common_budget_daily_limit=getattr(
            adv_setting, "common_budget_daily_limit", None
        ),
        common_budget_total_limit=getattr(
            adv_setting, "common_budget_total_limit", 0
        ),
        auto_adv_id=adv_setting.adv_id,
        search_adv_id=getattr(adv_setting, "search_adv_id", None),
        search_adv_active_status_str=getattr(
            adv_setting, "search_adv_active_status_str", None
        ),
        adv_id=adv_setting.adv_id,
    )


def _build_fake_complex_adv(**adv_setting_overrides: object) -> SimpleNamespace:
    adv_setting = _build_adv_setting()
    for key, value in adv_setting_overrides.items():
        setattr(adv_setting, key, value)
    return _wrap_complex_adv(adv_setting)


@pytest.fixture
def complex_adv() -> SimpleNamespace:
    return _build_fake_complex_adv(
        use_common_budget=True,
        search_adv_id=43,
        common_budget_daily_limit=500,
    )


@pytest.fixture(autouse=True)
def _patch_wb_shop_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        AutoBudgetService,
        "_get_wb_shop_id",
        AsyncMock(return_value="test-shop"),
    )


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
        _build_fake_complex_adv(id=1),
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
        _build_fake_complex_adv(id=42),
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


def test_allocation_fields_from_decision_persist_promo_metadata() -> None:
    decision = TopUpBalanceDecision(
        balance_type=0,
        balance_name="balance",
        cashback=CashbackTopup(
            cashback_sum=200,
            cashback_percent=50,
            expiration_date="2026-04-03T21:00:00Z",
        ),
    )
    promo_amount, promo_percent, expires, ordinary = (
        AutoBudgetService._allocation_fields_from_decision(decision, 1000)
    )
    assert promo_amount == 200
    assert promo_percent == 50
    assert ordinary == 800
    assert expires is not None


def test_get_campaign_config_uses_promo_auto_budget_when_overlay_active() -> None:
    adv_setting = SimpleNamespace(
        id=1,
        adv_id=42,
        search_adv_id=None,
        auto_budget_daily_limit=1000,
        search_auto_budget_daily_limit=0,
    )
    overlay = SimpleNamespace(
        active=True,
        PromoAutoBudget=1250,
        PropoSearchBudget=0,
    )
    complex_adv = _wrap_complex_adv(adv_setting)
    complex_adv.effective_promo_plan = overlay
    config = AutoBudgetService.get_campaign_config(complex_adv, AdvType.AUTO)
    assert config is not None
    assert config.limit == 1250


def test_get_campaign_config_selects_search_when_active() -> None:
    adv_setting = SimpleNamespace(
        id=1,
        adv_id=1,
        search_adv_id=200,
        auto_budget_daily_limit=0,
        search_auto_budget_daily_limit=500,
        auto_budget_balance_type="balance",
        search_auto_budget_balance_type="bonus",
    )

    complex_adv = _wrap_complex_adv(adv_setting)
    config = AutoBudgetService.get_campaign_config(
        complex_adv,
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


def test_pick_cashback_for_topup_skips_expired_prefers_earliest_live_fefo() -> None:
    """Expired April/May 2026 не выбираются при now=Sep 2026; live FEFO — October."""
    from datetime import datetime, timezone

    now = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)
    response = _FakeBalanceResponse(
        balance=0,
        net=5000,
        bonus=0,
        cashbacks=[
            {
                "sum": 99999,
                "percent": 50,
                "expiration_date": "2026-10-03T21:00:00Z",
            },
            {
                "sum": 1000,
                "percent": 40,
                "expiration_date": "2026-04-03T21:00:00Z",
            },
            {
                "sum": 2000,
                "percent": 45,
                "expiration_date": "2026-05-03T21:00:00Z",
            },
        ],
    )

    cashback = pick_cashback_for_topup(response, topup_amount=1000, now=now)

    assert cashback is not None
    assert cashback.cashback_percent == 50
    assert cashback.cashback_sum == 500
    assert cashback.expiration_date == "2026-10-03T21:00:00Z"


def test_select_topup_balance_decision_prefers_non_bonus_when_cashback_present() -> None:
    response = _FakeBalanceResponse(
        balance=0,
        net=3000,
        bonus=1200,
        cashbacks=[
            {
                "sum": 2000,
                "percent": 50,
                "expiration_date": "2026-12-03T21:00:00Z",
            }
        ],
    )

    decision = select_topup_balance_decision(response, topup_amount=1000)

    assert decision.balance_name == "net"
    assert decision.balance_type == 1
    assert decision.cashback is not None
    assert decision.cashback.cashback_sum == 500
    assert decision.cashback.cashback_percent == 50


def test_select_topup_balance_decision_ordinary_covers_remainder_only() -> None:
    response = _FakeBalanceResponse(
        balance=0,
        net=600,
        bonus=5000,
        cashbacks=[
            {
                "sum": 2000,
                "percent": 50,
                "expiration_date": "2026-12-03T21:00:00Z",
            }
        ],
    )
    decision = select_topup_balance_decision(response, topup_amount=1000)
    assert decision.balance_name == "net"
    assert decision.cashback is not None
    assert decision.cashback.cashback_sum == 500


def test_select_topup_balance_decision_allows_full_cashback_without_ordinary_balance() -> None:
    """100% WB cashback покрывает весь top-up; type остаётся обязательным для API."""
    response = _FakeBalanceResponse(
        balance=0,
        net=0,
        bonus=0,
        cashbacks=[
            {
                "sum": 5000,
                "percent": 100,
                "expiration_date": "2026-12-03T21:00:00Z",
            }
        ],
    )

    decision = select_topup_balance_decision(response, topup_amount=1000)

    assert decision.balance_type == 0
    assert decision.balance_name == "balance"
    assert decision.cashback is not None
    assert decision.cashback.cashback_sum == 1000
    assert decision.cashback.cashback_percent == 100


def test_select_topup_balance_decision_drops_promo_if_remainder_unfunded() -> None:
    response = _FakeBalanceResponse(
        balance=0,
        net=100,
        bonus=5000,
        cashbacks=[
            {
                "sum": 2000,
                "percent": 50,
                "expiration_date": "2026-12-03T21:00:00Z",
            }
        ],
    )
    decision = select_topup_balance_decision(response, topup_amount=1000)
    assert decision.cashback is None
    assert decision.balance_name == "bonus"


def test_cashback_summary_collects_total_best_percent_and_earliest_date() -> None:
    response = _FakeBalanceResponse(
        balance=0,
        net=0,
        bonus=0,
        cashbacks=[
            {
                "sum": 1000,
                "percent": 30,
                "expiration_date": "2026-04-10T21:00:00Z",
            },
            {
                "sum": 2000,
                "percent": 50,
                "expiration_date": "2026-04-03T21:00:00Z",
            },
        ],
    )

    summary = cashback_summary_from_response(response)

    assert summary.total == 3000
    assert summary.best_percent == 50
    assert summary.earliest_expiration_date == "2026-04-03T21:00:00Z"


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
        top_up_budget=AsyncMock(return_value=SimpleNamespace(total=600, raw={"ok": True})),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.select_topup_balance_decision",
        lambda response, *, topup_amount: SimpleNamespace(
            balance_name="balance_type",
            cashback=None,
        ),
    )
    service = AutoBudgetService(redis_client=_FakeRedis())
    wb_manager_hub = _build_wb_manager_hub()
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_budget_locked(
        complex_adv,
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
        "app.modules.auto_budget_manager.service.select_topup_balance_decision",
        lambda response, *, topup_amount: SimpleNamespace(
            balance_name="balance_type",
            cashback=None,
        ),
    )
    service = AutoBudgetService(redis_client=_FakeRedis())
    wb_manager_hub = _build_wb_manager_hub()
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        campaign_type=AdvType.AUTO,
        wb_manager_hub=wb_manager_hub,
    )

    assert result.status == AutoBudgetEnsureStatus.LIMIT_REACHED
    assert result.reason == "Daily top-up attempts doubled exceed limit"
    assert result.available_limit == 0


@pytest.mark.asyncio
async def test_ensure_common_budget_skips_when_lock_busy(monkeypatch, complex_adv) -> None:
    fake_redis = _FakeRedis()
    fake_redis.is_locked = True
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    service = AutoBudgetService(redis_client=fake_redis)
    inner = AsyncMock()
    monkeypatch.setattr(service, "_ensure_common_budget_locked", inner)

    result = await service.ensure_common_budget(
        complex_adv,
        adv_setting_id=1,
        wb_manager_hub=MagicMock(),
    )

    assert result is not None
    assert result.status == AutoBudgetEnsureStatus.LOCK_BUSY
    inner.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_common_budget_releases_lock(monkeypatch, complex_adv) -> None:
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
        complex_adv,
        adv_setting_id=complex_adv.original_adv_setting_id,
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
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_common_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        wb_manager_hub=MagicMock(),
    )

    assert result.status == AutoBudgetEnsureStatus.LIMIT_REACHED
    assert result.reason == "Daily successful top-ups already reached limit"
    assert result.available_limit == 0
    assert result.spend_today == 0.0


@pytest.mark.asyncio
async def test_ensure_budget_locked_blocks_topup_when_total_limit_exceeded(
    monkeypatch,
) -> None:
    """Раздельный режим: абсолютный лимит ноги исчерпан — пополнения нет."""
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    adv_setting = _build_adv_setting()
    adv_setting.auto_budget_total_limit = 500
    _patch_adv_setting(monkeypatch, adv_setting)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_daily_topup_sums",
        AsyncMock(return_value=(0.0, 0.0)),
    )
    total_spend_mock = AsyncMock(return_value=600.0)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_total_spend",
        total_spend_mock,
    )
    monkeypatch.setattr(
        AutoBudgetService,
        "_get_last_full_stat_update",
        AsyncMock(
            return_value=datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=3))
            )
        ),
    )

    service = AutoBudgetService(redis_client=_FakeRedis())
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        campaign_type=AdvType.AUTO,
        wb_manager_hub=_build_wb_manager_hub(),
    )

    assert result.status == AutoBudgetEnsureStatus.LIMIT_REACHED
    assert result.reason == "Total budget limit exceeded"
    assert result.available_limit == 0
    total_spend_mock.assert_awaited_once_with([adv_setting.adv_id])


@pytest.mark.asyncio
async def test_ensure_budget_locked_blocks_topup_when_total_spend_unknown(
    monkeypatch,
) -> None:
    """Сбой ClickHouse при заданном абсолютном лимите блокирует пополнение."""
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    adv_setting = _build_adv_setting()
    adv_setting.auto_budget_total_limit = 500
    _patch_adv_setting(monkeypatch, adv_setting)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_daily_topup_sums",
        AsyncMock(return_value=(0.0, 0.0)),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_total_spend",
        AsyncMock(side_effect=RuntimeError("clickhouse down")),
    )
    monkeypatch.setattr(
        AutoBudgetService,
        "_get_last_full_stat_update",
        AsyncMock(
            return_value=datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=3))
            )
        ),
    )

    wb_manager_hub = _build_wb_manager_hub()
    service = AutoBudgetService(redis_client=_FakeRedis())
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        campaign_type=AdvType.AUTO,
        wb_manager_hub=wb_manager_hub,
    )

    assert result.status == AutoBudgetEnsureStatus.ERROR
    assert result.reason == "Total budget spend unknown — top-up blocked"
    wb_manager_hub.wb_modifier.top_up_budget.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_common_budget_locked_blocks_topup_when_total_spend_unknown(
    monkeypatch,
) -> None:
    """Общий режим: недоступная статистика тоже блокирует пополнение."""
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    adv_setting = _build_common_adv_setting()
    adv_setting.common_budget_total_limit = 500
    _patch_adv_setting(monkeypatch, adv_setting)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_daily_topup_sums_common",
        AsyncMock(return_value=(0.0, 0.0)),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_total_spend",
        AsyncMock(side_effect=RuntimeError("clickhouse down")),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_last_full_stat_update",
        AsyncMock(
            return_value=datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=3))
            )
        ),
    )

    service = AutoBudgetService(redis_client=_FakeRedis())
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_common_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        wb_manager_hub=MagicMock(),
    )

    assert result.status == AutoBudgetEnsureStatus.ERROR
    assert result.reason == "Total budget spend unknown — top-up blocked"


@pytest.mark.asyncio
async def test_ensure_budget_locked_ignores_total_limit_when_zero(monkeypatch) -> None:
    """Абсолютный лимит 0 = выключено: all-time расход даже не запрашивается."""
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    adv_setting = _build_adv_setting()
    adv_setting.auto_budget_total_limit = 0
    _patch_adv_setting(monkeypatch, adv_setting)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_daily_topup_sums",
        AsyncMock(return_value=(0.0, 0.0)),
    )
    total_spend_mock = AsyncMock(return_value=1_000_000.0)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_total_spend",
        total_spend_mock,
    )
    monkeypatch.setattr(
        AutoBudgetService,
        "_get_last_full_stat_update",
        AsyncMock(
            return_value=datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=3))
            )
        ),
    )

    service = AutoBudgetService(redis_client=_FakeRedis())
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        campaign_type=AdvType.AUTO,
        wb_manager_hub=_build_wb_manager_hub(),
    )

    assert result.reason != "Total budget limit exceeded"
    total_spend_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_common_budget_locked_blocks_topup_when_total_limit_exceeded(
    monkeypatch,
) -> None:
    """Общий режим: абсолютный лимит считается по сумме обеих ног."""
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings", _build_settings()
    )
    adv_setting = _build_common_adv_setting()
    adv_setting.common_budget_total_limit = 500
    _patch_adv_setting(monkeypatch, adv_setting)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_daily_topup_sums_common",
        AsyncMock(return_value=(0.0, 0.0)),
    )
    total_spend_mock = AsyncMock(return_value=600.0)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_total_spend",
        total_spend_mock,
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._get_last_full_stat_update",
        AsyncMock(
            return_value=datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=3))
            )
        ),
    )

    service = AutoBudgetService(redis_client=_FakeRedis())
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_common_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        wb_manager_hub=MagicMock(),
    )

    assert result.status == AutoBudgetEnsureStatus.LIMIT_REACHED
    assert result.reason == "Total budget limit exceeded"
    assert result.available_limit == 0
    total_spend_mock.assert_awaited_once_with(
        [adv_setting.adv_id, adv_setting.search_adv_id]
    )


@pytest.mark.asyncio
async def test_ensure_common_budget_rejects_when_one_campaign_has_stale_stats(
    monkeypatch,
) -> None:
    """When Auto has fresh stats and Search has stale (or vice versa), reject with NOT_NEW_ADV_STATS."""
    period = 600
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(
            UPDATE_FULL_ADV_STAT_PERIOD=period,
            AUTO_BUDGET_MIN_BALANCE=500,
        ),
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

    wb_modifier = SimpleNamespace(
        get_campaign_budget=AsyncMock(
            return_value=SimpleNamespace(total=600, raw={}),
        ),
    )
    wb_manager_hub = SimpleNamespace(wb_modifier=wb_modifier)
    service = AutoBudgetService(redis_client=_FakeRedis())
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_common_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        wb_manager_hub=wb_manager_hub,
    )

    assert result.status == AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS
    assert result.reason == "Last full adv stats too old"


@pytest.mark.asyncio
async def test_refresh_promo_state_applies_fresh_snapshot_to_current_advs() -> None:
    """Watchdog refresh должен обновить уже построенные DTO без следующего тика."""
    updated_at = datetime.datetime.now(datetime.timezone.utc)
    cached_state = CachedShopPromoState(
        updated_at=updated_at,
        topup_amount=1000,
        pool_usable=False,
        pool_amount=0,
        pool_fraction=Decimal("0"),
        campaigns={
            11: CachedCampaignPromoState(
                remaining=200,
                fraction=Decimal("0.2"),
                expires_at=None,
                usable=True,
                effective_fraction=Decimal("0.2"),
                pool_usable=False,
                campaign_usable=True,
            )
        },
    )
    adv_setting = SimpleNamespace(
        raise_plan_on_promobonuses=True,
        plan_for_sales_for_day=10,
        target_price_for_order=100.0,
        max_price_for_order=200.0,
        auto_budget_daily_limit=1000,
        search_auto_budget_daily_limit=0,
        common_budget_daily_limit=None,
    )
    complex_adv = SimpleNamespace(
        adv_setting=adv_setting,
        adv_id=11,
        search_adv_id=None,
        promo_fraction=Decimal("0"),
        promo_multiplier=Decimal("1"),
        effective_promo_plan=None,
    )
    service = AutoBudgetService(redis_client=_FakeRedis())
    service._promo_state_service.refresh = AsyncMock()
    service._promo_state_manager.get = AsyncMock(return_value=cached_state)

    await service.refresh_promo_state(
        [complex_adv],
        SimpleNamespace(wb_modifier=SimpleNamespace()),
        "shop-1",
    )

    assert complex_adv.promo_fraction == Decimal("0.2")
    assert complex_adv.effective_promo_plan is not None


@pytest.mark.asyncio
async def test_ensure_common_budget_rejects_when_both_campaigns_have_stale_stats(
    monkeypatch,
) -> None:
    """When both timestamps are stale, reject with NOT_NEW_ADV_STATS."""
    period = 600
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(
            UPDATE_FULL_ADV_STAT_PERIOD=period,
            AUTO_BUDGET_MIN_BALANCE=500,
        ),
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

    wb_modifier = SimpleNamespace(
        get_campaign_budget=AsyncMock(
            return_value=SimpleNamespace(total=600, raw={}),
        ),
    )
    wb_manager_hub = SimpleNamespace(wb_modifier=wb_modifier)
    service = AutoBudgetService(redis_client=_FakeRedis())
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_common_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        wb_manager_hub=wb_manager_hub,
    )

    assert result.status == AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS
    assert result.reason == "Last full adv stats too old"


@pytest.mark.asyncio
async def test_ensure_common_budget_allows_search_topup_when_campaign_missing_stats_and_search_needs_cold_start(
    monkeypatch,
) -> None:
    """Missing stats must not block cold-start SEARCH top-up when live WB budgets are low."""
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(AUTO_BUDGET_MIN_BALANCE=500),
    )
    adv_setting = _build_common_adv_setting()
    adv_setting.search_adv_active_status_str = WBAdvActiveStatus.PAUSE
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

    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.select_topup_balance_decision",
        lambda response, *, topup_amount: SimpleNamespace(
            balance_name="balance",
            cashback=None,
        ),
    )

    wb_modifier = SimpleNamespace(
        get_campaign_budget=AsyncMock(
            side_effect=[
                SimpleNamespace(total=0, raw={"total": 0}),
                SimpleNamespace(total=0, raw={"total": 0}),
            ]
        ),
        get_campaign_balance=AsyncMock(
            return_value=_FakeBalanceResponse(balance=0, net=5000, bonus=0, cashbacks=None)
        ),
        top_up_budget=AsyncMock(return_value=SimpleNamespace(raw={"ok": True})),
    )
    wb_manager_hub = SimpleNamespace(wb_modifier=wb_modifier)

    mark_topup_entry = AsyncMock()
    create_topup_entry = AsyncMock(return_value=SimpleNamespace(id=777))
    monkeypatch.setattr(service := AutoBudgetService(redis_client=_FakeRedis()), "_create_topup_entry", create_topup_entry)
    monkeypatch.setattr(service, "_mark_topup_entry", mark_topup_entry)

    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_common_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        wb_manager_hub=wb_manager_hub,
    )

    assert result.status == AutoBudgetEnsureStatus.TOPUP_UNVERIFIED
    assert result.campaign_type == AdvType.SEARCH
    assert result.adv_id == adv_setting.search_adv_id
    assert result.reason is None
    wb_modifier.top_up_budget.assert_awaited_once()
    assert wb_modifier.top_up_budget.await_args.kwargs["adv_id"] == adv_setting.search_adv_id
    create_topup_entry.assert_awaited_once()
    assert create_topup_entry.await_args.kwargs["adv_id"] == adv_setting.search_adv_id
    assert create_topup_entry.await_args.kwargs["campaign_type"] == AdvType.SEARCH


@pytest.mark.asyncio
async def test_ensure_common_budget_rejects_when_one_campaign_missing_stats_and_budgets_already_sufficient(
    monkeypatch,
) -> None:
    """Missing stats should still block when live WB budgets are already above the threshold."""
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(AUTO_BUDGET_MIN_BALANCE=500),
    )
    adv_setting = _build_common_adv_setting()
    adv_setting.search_adv_active_status_str = WBAdvActiveStatus.PAUSE
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

    wb_modifier = SimpleNamespace(
        get_campaign_budget=AsyncMock(
            side_effect=[
                SimpleNamespace(total=600, raw={"total": 600}),
                SimpleNamespace(total=600, raw={"total": 600}),
            ]
        ),
    )
    wb_manager_hub = SimpleNamespace(wb_modifier=wb_modifier)
    service = AutoBudgetService(redis_client=_FakeRedis())
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_common_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        wb_manager_hub=wb_manager_hub,
    )

    assert result.status == AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS
    assert result.reason == "Missing full adv stats for one or both campaigns"


@pytest.mark.asyncio
async def test_ensure_budget_rejects_when_stats_not_refreshed(monkeypatch) -> None:
    period = 600
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(
            UPDATE_FULL_ADV_STAT_PERIOD=period,
            AUTO_BUDGET_MIN_BALANCE=500,
        ),
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
            return_value=SimpleNamespace(total=2000, raw={"current": 2000})
        ),
        get_campaign_balance=AsyncMock(return_value={"balance": []}),
        top_up_budget=AsyncMock(return_value=SimpleNamespace(total=100, raw={"ok": True})),
    )
    wb_manager_hub = SimpleNamespace(wb_modifier=wb_modifier)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.select_topup_balance_decision",
        lambda response, *, topup_amount: SimpleNamespace(
            balance_name="balance_type",
            cashback=None,
        ),
    )
    service = AutoBudgetService(redis_client=_FakeRedis())
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        campaign_type=AdvType.AUTO,
        wb_manager_hub=wb_manager_hub,
    )

    assert result.status == AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS
    assert result.reason == "Last Update Full Adv Stats too old"
    assert result.spend_today == 0.0


def test_stale_stats_wb_total_threshold(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(
            AUTO_BUDGET_MIN_BALANCE=0,
            AUTO_BUDGET_TOPUP_AMOUNT=777,
        ),
    )
    service = AutoBudgetService(redis_client=_FakeRedis())
    assert service._stale_stats_wb_total_threshold() == 777

    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(
            AUTO_BUDGET_MIN_BALANCE=0,
            AUTO_BUDGET_TOPUP_AMOUNT=0,
        ),
    )
    service_zero_topup = AutoBudgetService(redis_client=_FakeRedis())
    assert service_zero_topup._stale_stats_wb_total_threshold() == 1

    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(AUTO_BUDGET_MIN_BALANCE=300),
    )
    service_min = AutoBudgetService(redis_client=_FakeRedis())
    assert service_min._stale_stats_wb_total_threshold() == 300


@pytest.mark.asyncio
async def test_ensure_budget_rejects_stale_when_min_balance_zero_but_wb_high(
    monkeypatch,
) -> None:
    """With MIN_BALANCE=0, stale gate must still apply using top-up step as threshold."""
    period = 600
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(
            UPDATE_FULL_ADV_STAT_PERIOD=period,
            AUTO_BUDGET_MIN_BALANCE=0,
            AUTO_BUDGET_TOPUP_AMOUNT=1000,
        ),
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
            return_value=SimpleNamespace(total=2000, raw={"current": 2000})
        ),
        get_campaign_balance=AsyncMock(return_value={"balance": []}),
        top_up_budget=AsyncMock(return_value=SimpleNamespace(total=100, raw={"ok": True})),
    )
    wb_manager_hub = SimpleNamespace(wb_modifier=wb_modifier)
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.select_topup_balance_decision",
        lambda response, *, topup_amount: SimpleNamespace(
            balance_name="balance_type",
            cashback=None,
        ),
    )
    service = AutoBudgetService(redis_client=_FakeRedis())
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.AutoBudgetService._calculate_spend_today",
        AsyncMock(return_value=0.0),
    )
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        campaign_type=AdvType.AUTO,
        wb_manager_hub=wb_manager_hub,
    )

    assert result.status == AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS
    assert result.reason == "Last Update Full Adv Stats too old"


@pytest.mark.asyncio
async def test_ensure_common_budget_rejects_stale_when_min_zero_both_wb_high(
    monkeypatch,
) -> None:
    period = 600
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.service.settings",
        _build_settings(
            UPDATE_FULL_ADV_STAT_PERIOD=period,
            AUTO_BUDGET_MIN_BALANCE=0,
            AUTO_BUDGET_TOPUP_AMOUNT=1000,
        ),
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

    wb_modifier = SimpleNamespace(
        get_campaign_budget=AsyncMock(
            return_value=SimpleNamespace(total=2000, raw={}),
        ),
    )
    wb_manager_hub = SimpleNamespace(wb_modifier=wb_modifier)
    service = AutoBudgetService(redis_client=_FakeRedis())
    complex_adv = _wrap_complex_adv(adv_setting)
    result = await service._ensure_common_budget_locked(
        complex_adv,
        adv_setting_id=adv_setting.id,
        wb_manager_hub=wb_manager_hub,
    )

    assert result.status == AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS
    assert result.reason == "Last full adv stats too old"
