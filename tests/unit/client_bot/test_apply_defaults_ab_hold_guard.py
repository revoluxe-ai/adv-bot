"""Unit-тесты: shared defaults / «Применить дефолты» ↔ A/B Hold guard.

Spec ``card-ab-hold-mode`` требование «Shared defaults MUST NOT disable or mutate
A/B Hold on a held campaign» / decision ``card-ab-hold-write-path-ownership`` §13:
«Применить дефолты» (`apply_defaults_to_adv_setting` + handlers) — **не**
enable/disable path A/B Hold. Для кампании в ``PENDING_SETUP`` / ``ACTIVE`` этот
путь не отключает и не мутирует режим (mode / allowed-set snapshot / coupled
structural флаги сохраняются); disable — только owned paid Telegram EXIT.

Покрывает:
- 15.1 helper no-op на held (ACTIVE/PENDING) + paired positive apply на OFF;
- 15.2 handler-level: single refuse (без un-owned disable, без commit) + apply на
  OFF; shop-wide skip held (сохранены) + apply non-held + honest counter.

Падали бы до фикса: helper безусловно форсил ``card_ab_hold_mode='off'`` +
сбрасывал ``bot_active`` / coupled structural; handlers коммитили это как success.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.modules.default_settings import apply_defaults_to_adv_setting
from app.client_bot.user_interface.handlers.adv_setting.adv_setting import (
    apply_campaign_defaults,
    apply_defaults_for_shop,
)
from app.client_bot.user_interface.views.callbacks import (
    ApplyCampaignDefaults,
    ApplyDefaultsForShop,
)
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import (
    BidderCoroutineType,
    BidderMode,
)

_HANDLER = "app.client_bot.user_interface.handlers.adv_setting.adv_setting"


# --- 15.1: helper (write boundary = поля AdvSetting) ---


def _held_adv(mode: str) -> SimpleNamespace:
    """Held-кампания (V3, ACTIVE/PENDING) со снапшотом — маркеры un-owned disable."""
    return SimpleNamespace(
        id=1,
        card_ab_hold_mode=mode,
        card_ab_hold_allowed_phrases_snapshot=["good1", "good2"],
        bot_active=True,
        auto_update_white_list=False,
        auto_update_target_place=False,
        bidder_active=False,
        max_place=7,
        max_cpm=42,
        wb_cabinet=SimpleNamespace(default_max_cpm=999),
    )


def _off_adv() -> SimpleNamespace:
    """OFF-кампания со «стартовыми» значениями, отличными от дефолтов."""
    return SimpleNamespace(
        id=2,
        card_ab_hold_mode="off",
        card_ab_hold_allowed_phrases_snapshot=[],
        bot_active=True,
        bidder_active=False,
        bidder_for_auto=False,
        bidder_mode=None,
        bidder_coroutine_type=None,
        orders_source_for_auto_mode=None,
        sales_predict_method=None,
        auto_update_white_list=False,
        auto_update_target_place=False,
        auto_budget_watchdog_enabled=False,
        use_common_budget=False,
        target_ctr_mode=True,
        new_auto_min_ctr_mode=True,
        reset_place=False,
        max_place=1,
        max_cpm=5,
        wb_cabinet=SimpleNamespace(default_max_cpm=999),
    )


def _assert_common_defaults(adv: SimpleNamespace) -> None:
    """Проверить только поля, принадлежащие common defaults policy."""
    assert adv.bidder_mode == BidderMode.BY_POSITIONS
    assert adv.bidder_coroutine_type == BidderCoroutineType.UPDATE_CLUSTER_BIDS
    assert adv.orders_source_for_auto_mode == OrdersSourceForAutoMode.COMMON_STATISTIC
    assert adv.sales_predict_method == FactMethods.BY_CARTS
    assert adv.auto_budget_watchdog_enabled is True
    assert adv.use_common_budget is True
    assert adv.target_ctr_mode is False
    assert adv.new_auto_min_ctr_mode is False
    assert adv.reset_place is True


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["active", "pending_setup"])
def test_helper_noop_on_held_campaign(mode: str) -> None:
    """15.1: held → helper no-op (mode/snapshot/coupled поля не тронуты)."""
    adv = _held_adv(mode)
    apply_defaults_to_adv_setting(adv, adv.wb_cabinet)  # type: ignore[arg-type]
    assert adv.card_ab_hold_mode == mode
    assert adv.card_ab_hold_allowed_phrases_snapshot == ["good1", "good2"]
    assert adv.bot_active is True
    assert adv.auto_update_white_list is False
    assert adv.auto_update_target_place is False


@pytest.mark.unit
def test_helper_applies_defaults_on_off_campaign() -> None:
    """15.1 paired positive: OFF → common defaults policy применена."""
    adv = _off_adv()
    apply_defaults_to_adv_setting(adv, adv.wb_cabinet)  # type: ignore[arg-type]
    _assert_common_defaults(adv)
    assert adv.card_ab_hold_mode == "off"


# --- 15.2: handler-level (write boundary = commit + значения полей) ---


class _Result:
    """Минимальный async-result: scalar_one/scalar/scalars под нужды handlers."""

    def __init__(
        self,
        *,
        adv: object | None = None,
        wb_user_cabinet: object | None = None,
        advs: list[object] | None = None,
    ) -> None:
        self._adv = adv
        self._wbc = wb_user_cabinet
        self._advs = advs

    def scalar_one(self) -> object | None:
        return self._adv

    def scalar_one_or_none(self) -> object | None:
        if self._adv is not None:
            return self._adv
        return self._wbc

    def unique(self) -> "_Result":
        return self

    def scalar(self) -> object | None:
        return self._wbc

    def scalars(self) -> SimpleNamespace:
        advs = list(self._advs or [])
        return SimpleNamespace(all=lambda: advs)


class _Session:
    """Async-сессия, записывающая execute/commit (без реальной БД)."""

    def __init__(
        self,
        *,
        adv: object | None = None,
        wb_user_cabinet: object | None = None,
        advs: list[object] | None = None,
        recorder: list[str],
    ) -> None:
        self._adv = adv
        self._wbc = wb_user_cabinet
        self._advs = advs
        self._recorder = recorder
        self._execute_count = 0

    async def execute(self, _stmt: object) -> _Result:
        self._recorder.append("execute")
        self._execute_count += 1
        if self._advs is not None:
            return _Result(advs=self._advs)
        if self._execute_count == 1:
            return _Result(wb_user_cabinet=self._wbc)
        return _Result(adv=self._adv)

    async def commit(self) -> None:
        self._recorder.append("commit")

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False


def _session_maker(
    *,
    adv: object | None = None,
    wb_user_cabinet: object | None = None,
    advs: list[object] | None = None,
    recorder: list[str],
):
    """Фабрика, совместимая с ``sm`` / ``sm(read_only=...)``."""

    def _sm(*_a: object, **_kw: object) -> _Session:
        return _Session(
            adv=adv,
            wb_user_cabinet=wb_user_cabinet,
            advs=advs,
            recorder=recorder,
        )

    return _sm


def _callback(chat_id: int = 100, user_id: int = 9001) -> SimpleNamespace:
    """Минимальный CallbackQuery: chat id и telegram user id."""
    return SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=chat_id)),
        from_user=SimpleNamespace(id=user_id),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_campaign_defaults_blocks_held_campaign() -> None:
    """15.2: single handler на held → нет un-owned disable, нет commit, mode сохранён."""
    adv = _held_adv("active")
    wb_user_cabinet = SimpleNamespace(id=2, wb_cabinet_id=31, wb_cabinet=adv.wb_cabinet)
    recorder: list[str] = []
    bot = AsyncMock()

    with (
        patch(
            f"{_HANDLER}.sm",
            _session_maker(adv=adv, wb_user_cabinet=wb_user_cabinet, recorder=recorder),
        ),
        patch(f"{_HANDLER}.AdvSettingMenu", MagicMock(return_value=AsyncMock())),
    ):
        await apply_campaign_defaults(
            _callback(),  # type: ignore[arg-type]
            ApplyCampaignDefaults(
                adv_setting_original_id=1, wb_user_cabinet_original_id=2
            ),
            bot,
        )

    assert adv.card_ab_hold_mode == "active"
    assert adv.card_ab_hold_allowed_phrases_snapshot == ["good1", "good2"]
    assert adv.bot_active is True
    assert "commit" not in recorder
    sent = " ".join(str(c.args[1]) for c in bot.send_message.call_args_list)
    assert "A/B Hold" in sent
    assert "успешно" not in sent


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_campaign_defaults_applies_off_campaign() -> None:
    """15.2 paired positive: single handler на OFF → дефолты применены + commit."""
    adv = _off_adv()
    wb_user_cabinet = SimpleNamespace(id=2, wb_cabinet_id=31, wb_cabinet=adv.wb_cabinet)
    recorder: list[str] = []
    bot = AsyncMock()

    with (
        patch(
            f"{_HANDLER}.sm",
            _session_maker(adv=adv, wb_user_cabinet=wb_user_cabinet, recorder=recorder),
        ),
        patch(f"{_HANDLER}.AdvSettingMenu", MagicMock(return_value=AsyncMock())),
    ):
        await apply_campaign_defaults(
            _callback(),  # type: ignore[arg-type]
            ApplyCampaignDefaults(
                adv_setting_original_id=2, wb_user_cabinet_original_id=2
            ),
            bot,
        )

    _assert_common_defaults(adv)
    assert adv.card_ab_hold_mode == "off"
    assert "commit" in recorder
    sent = " ".join(str(c.args[1]) for c in bot.send_message.call_args_list)
    assert "успешно" in sent


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_defaults_for_shop_skips_held_applies_rest() -> None:
    """15.2: shop-wide → held сохранены (не отключены), non-held получают дефолты."""
    held = _held_adv("active")
    off = _off_adv()
    recorder: list[str] = []
    bot = AsyncMock()
    state = MagicMock()

    with (
        patch(
            f"{_HANDLER}.sm",
            _session_maker(advs=[held, off], recorder=recorder),
        ),
        patch(f"{_HANDLER}.ShopMenu", MagicMock(return_value=AsyncMock())),
    ):
        await apply_defaults_for_shop(
            _callback(),  # type: ignore[arg-type]
            ApplyDefaultsForShop(wb_user_cabinet_original_id=2),
            bot,
            state,
        )

    # held сохранён — un-owned disable не выполнен
    assert held.card_ab_hold_mode == "active"
    assert held.card_ab_hold_allowed_phrases_snapshot == ["good1", "good2"]
    assert held.bot_active is True
    # non-held получил дефолты
    _assert_common_defaults(off)
    # honest counter: 1 применён, 1 пропущен
    sent = " ".join(str(c.args[1]) for c in bot.send_message.call_args_list)
    assert "применены к 1" in sent
    assert "Пропущено кампаний в режиме A/B Hold: 1" in sent
