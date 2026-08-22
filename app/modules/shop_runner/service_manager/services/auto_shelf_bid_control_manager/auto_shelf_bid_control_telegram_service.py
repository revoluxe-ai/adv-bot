"""Сервис Telegram-действий для управления ставкой полок Auto-РК."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Protocol, cast

from app.core.mp.wb.api.managers.wb_promotion_manager.wb_promotion_manager import (
    WBModifier,
)
from app.core.redis_manager_v2.redis_client import RedisClient
from app.settings import settings
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv.complex_adv import (
    ComplexAdv,
    resolve_auto_shelf_bid_control_strategy,
)
from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost_from_summary
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)

from .auto_shelf_bid_control_repository import AutoShelfBidControlRepository
from .auto_shelf_bid_control_manager import (
    AutoShelfBidControlManager,
    MainBidRefreshResult,
)
from .auto_shelf_bid_control_view_provider import AutoShelfBidControlViewProvider
from .auto_shelf_bid_setter import AutoShelfBidSetter
from .bid_units import format_bid_minor_for_telegram, rubles_to_bid_minor
from .dto import AutoShelfBidControlViewDTO


class _WbManagerHubProtocol(Protocol):
    wb_modifier: object


class _WbManagerHubFactoryProtocol(Protocol):
    def get_wb_manager_hub(self, shop_id: str) -> _WbManagerHubProtocol: ...


class _WbManagerHubFactoryContainerProtocol(Protocol):
    def wb_manager_hub_factory(self) -> _WbManagerHubFactoryProtocol: ...


class _ModuleResourcesProtocol(Protocol):
    wb_manager_hub_factory_container: _WbManagerHubFactoryContainerProtocol


class _DIContainerProtocol(Protocol):
    module_resources: _ModuleResourcesProtocol


@dataclass(slots=True)
class _TelegramBidSetterAdapter:
    """Adapter, который прокидывает Telegram PATCH через существующий setter path."""

    service: "AutoShelfBidControlTelegramService"
    adv: AdvSetting
    nmid: int

    async def set_bid(
        self,
        complex_adv: ComplexAdv,
        *,
        bid_minor: int,
        currency: str,
    ) -> None:
        set_bid = getattr(self.service, "_set_bid")
        await set_bid(
            adv=self.adv,
            nmid=self.nmid,
            bid_minor=int(bid_minor),
            currency=currency,
        )


@dataclass(slots=True)
class AutoShelfBidControlTelegramError(Exception):
    """Пользовательская ошибка сценария Telegram-управления."""

    message: str


_BID_UNITS_GATE_ERROR = (
    "Gate ставок не подтверждён: AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED=false"
)


class AutoShelfBidControlTelegramService:
    """Инкапсулирует действия Telegram UI без изменения core-алгоритма."""

    def __init__(
        self,
        *,
        redis_client: RedisClient,
        repository: AutoShelfBidControlRepository | None = None,
        view_provider: AutoShelfBidControlViewProvider | None = None,
    ) -> None:
        self._repository = repository or AutoShelfBidControlRepository()
        self._view_provider = view_provider or AutoShelfBidControlViewProvider(
            redis_client=redis_client,
            repository=self._repository,
        )
        self._bid_cache = RedisAutoRecommendationsBidValueManager(redis_client)

    async def build_view(self, adv_setting_original_id: int) -> AutoShelfBidControlViewDTO:
        """Построить текущее состояние экрана управления."""
        return await self._view_provider.build_view(adv_setting_original_id)

    async def apply_main_bid_refresh_if_needed(
        self,
        adv_setting_original_id: int,
    ) -> MainBidRefreshResult:
        """Применить main bid refresh до чтения view и вернуть результат."""
        # Keep Telegram/manual refresh aligned with worker ticks.
        # Transitional case: even after the migration, legacy `cycle_metric`
        # can still appear in tests, local dumps, or partially updated
        # environments. Worker paths normalize it through ComplexAdv
        # (`cycle_metric -> cpc`), so Telegram must normalize the same way
        # before building the lightweight complex_adv_like object.
        adv = await self._get_adv_or_raise(adv_setting_original_id)
        nmid = self._get_single_nmid_or_raise(adv)
        state = await self._repository.get_state(nmid)
        if state is None:
            return MainBidRefreshResult.SKIPPED_NOT_MAIN
        if state.current_mode != "main":
            return MainBidRefreshResult.SKIPPED_NOT_MAIN
        if not bool(adv.auto_shelf_bid_control_enabled):
            return MainBidRefreshResult.SKIPPED_DISABLED
        settings_obj = await self._repository.get_or_create_default_settings(nmid=nmid)
        min_bid_minor = await self._view_provider._fetch_wb_min_bid_minor(  # type: ignore[attr-defined]
            int(adv_setting_original_id),
            nmid,
        )
        if min_bid_minor is None:
            return MainBidRefreshResult.SKIPPED_NO_DESIRED_BID
        actual_bid_minor = None
        cached_bid = await self._bid_cache.get_bid(
            auto_adv_id=int(adv.adv_id),
            nmid=nmid,
        )
        if cached_bid is not None:
            actual_bid_minor = int(cached_bid.bid_minor)
        plan_fact_summary = await PlanFactReader().get_latest_plan_fact(int(adv.adv_id))
        normalized_strategy = resolve_auto_shelf_bid_control_strategy(
            getattr(adv, "auto_shelf_bid_control_strategy", None)
        )
        complex_adv_like = SimpleNamespace(
            main_nmid=nmid,
            auto_adv_id=int(adv.adv_id),
            nmids=[nmid],
            bot_active=bool(getattr(adv, "bot_active", True)),
            auto_adv_active_status=bool(getattr(adv, "auto_adv_active_status", True)),
            auto_shelf_bid_control_enabled=bool(adv.auto_shelf_bid_control_enabled),
            auto_shelf_bid_control_strategy=normalized_strategy,
            adv_setting=adv,
            original_max_cpo=float(adv.max_price_for_order or 0.0),
            fact_pay_for_order=(
                plan_fact_summary.fact_pay_for_order if plan_fact_summary else None
            ),
            resolve_cpo=resolve_target_cost_from_summary(
                plan_fact_summary,
                plan_orders=int(adv.plan_for_sales_for_day or 0),
                plan_target_pay_for_order=adv.target_price_for_order,
                plan_max_pay_for_order=adv.max_price_for_order,
            ),
        )
        manager = AutoShelfBidControlManager(
            bid_cache_manager=self._bid_cache,
            wb_bid_setter=cast(
                AutoShelfBidSetter,
                _TelegramBidSetterAdapter(self, adv, nmid),
            ),
            repository=self._repository,
            analytics_repository=self._view_provider._analytics,  # type: ignore[attr-defined]
        )
        # Telegram refresh is intentionally read-only.
        # We still build the exact same strategy-aware snapshot as the worker
        # tick, but we do not persist state or PATCH WB from the UI path.
        # This keeps `cycle_metric -> cpc` compatibility and strategy
        # explanations aligned without giving screen refresh stronger write
        # powers than the normal control loop.
        _ = await manager.build_decision_snapshot(
            complex_adv_like,  # type: ignore[arg-type]
            settings_obj=settings_obj,
            state=state,
            min_bid_minor=int(min_bid_minor),
            actual_bid_minor=actual_bid_minor,
            control_enabled=bool(adv.auto_shelf_bid_control_enabled),
        )
        return MainBidRefreshResult.NO_CHANGE

    async def enable(self, adv_setting_original_id: int) -> AutoShelfBidControlViewDTO:
        """Включить управление ставкой; при отсутствии settings создать default."""
        adv = await self._get_adv_or_raise(adv_setting_original_id)
        nmid = self._get_single_nmid_or_raise(adv)
        await self._repository.get_or_create_default_settings(nmid=nmid)
        view_before = await self.build_view(adv_setting_original_id)
        actual = view_before.actual_bid_minor
        max_bid = view_before.max_bid_minor
        # build_view мог записать legacy repair в БД — берём max из view, не stale settings.
        if actual is not None and max_bid is not None and int(max_bid) < int(actual):
            await self._repository.update_settings(
                nmid=nmid,
                max_bid_minor=int(actual),
            )
        await self._repository.set_enabled(adv_setting_original_id, True)
        return await self.build_view(adv_setting_original_id)

    async def disable(self, adv_setting_original_id: int) -> AutoShelfBidControlViewDTO:
        """Выключить управление ставкой, сохранив settings/state."""
        await self._get_adv_or_raise(adv_setting_original_id)
        await self._repository.set_enabled(adv_setting_original_id, False)
        return await self.build_view(adv_setting_original_id)

    async def update_max_bid(
        self,
        adv_setting_original_id: int,
        value: str,
    ) -> AutoShelfBidControlViewDTO:
        """Сохранить новое max_bid_minor без сброса цикла."""
        adv = await self._get_adv_or_raise(adv_setting_original_id)
        nmid = self._get_single_nmid_or_raise(adv)
        parsed_rub = self._parse_positive_int(
            value,
            "Ставка должна быть положительным числом (в рублях).",
        )
        parsed = rubles_to_bid_minor(parsed_rub)
        view = await self.build_view(adv_setting_original_id)
        min_bid_minor = view.min_bid_minor
        if min_bid_minor is None:
            raise AutoShelfBidControlTelegramError(
                "Максимальная ставка не может быть ниже минимальной ставки WB: "
                f"{format_bid_minor_for_telegram(view.min_bid_minor, view.currency)}"
            )
        if parsed < int(min_bid_minor):
            raise AutoShelfBidControlTelegramError(
                "Максимальная ставка не может быть ниже минимальной ставки WB: "
                f"{format_bid_minor_for_telegram(min_bid_minor, view.currency)}"
            )
        await self._repository.get_or_create_default_settings(nmid=nmid)
        await self._repository.update_settings(nmid=nmid, max_bid_minor=parsed)
        return await self.build_view(adv_setting_original_id)

    async def update_test_share(
        self,
        adv_setting_original_id: int,
        value: str,
    ) -> AutoShelfBidControlViewDTO:
        """Сохранить долю теста (поддержка `10` и `0.1`)."""
        adv = await self._get_adv_or_raise(adv_setting_original_id)
        nmid = self._get_single_nmid_or_raise(adv)
        parsed = self._parse_test_share(value)
        await self._repository.get_or_create_default_settings(nmid=nmid)
        await self._repository.update_settings(nmid=nmid, test_share=parsed)
        return await self.build_view(adv_setting_original_id)

    async def update_target_test_impressions(
        self,
        adv_setting_original_id: int,
        value: str,
    ) -> AutoShelfBidControlViewDTO:
        """Сохранить target_test_impressions без сброса state."""
        adv = await self._get_adv_or_raise(adv_setting_original_id)
        nmid = self._get_single_nmid_or_raise(adv)
        parsed = self._parse_positive_int(
            value,
            "Количество показов должно быть целым числом больше 0.",
        )
        await self._repository.get_or_create_default_settings(nmid=nmid)
        await self._repository.update_settings(nmid=nmid, target_test_impressions=parsed)
        return await self.build_view(adv_setting_original_id)

    async def update_target_test_observation_minutes(
        self,
        adv_setting_original_id: int,
        value: str,
    ) -> AutoShelfBidControlViewDTO:
        """Сохранить минимальное время теста, не меньше 60 минут."""
        adv = await self._get_adv_or_raise(adv_setting_original_id)
        nmid = self._get_single_nmid_or_raise(adv)
        parsed = self._parse_positive_int(
            value,
            "Минимальное время теста должно быть целым числом от 60 минут.",
        )
        if parsed < 60:
            raise AutoShelfBidControlTelegramError(
                "Минимальное время теста должно быть не меньше 60 минут."
            )
        await self._repository.get_or_create_default_settings(nmid=nmid)
        await self._repository.update_settings(
            nmid=nmid,
            target_test_observation_minutes=parsed,
        )
        return await self.build_view(adv_setting_original_id)

    async def update_min_bid_distance(
        self,
        adv_setting_original_id: int,
        value: str,
    ) -> AutoShelfBidControlViewDTO:
        """Сохранить min_bid_distance_minor без сброса state."""
        adv = await self._get_adv_or_raise(adv_setting_original_id)
        nmid = self._get_single_nmid_or_raise(adv)
        parsed_rub = self._parse_positive_int(
            value,
            "Шаг между тестовыми ставками: положительное число в рублях.",
        )
        parsed = rubles_to_bid_minor(parsed_rub)
        await self._repository.get_or_create_default_settings(nmid=nmid)
        await self._repository.update_settings(nmid=nmid, min_bid_distance_minor=parsed)
        return await self.build_view(adv_setting_original_id)

    async def update_retest_interval_days(
        self,
        adv_setting_original_id: int,
        value: str,
    ) -> AutoShelfBidControlViewDTO:
        """Сохранить календарный интервал перетеста (суток, default 7)."""
        adv = await self._get_adv_or_raise(adv_setting_original_id)
        nmid = self._get_single_nmid_or_raise(adv)
        parsed = self._parse_positive_int(
            value,
            "Интервал перетеста: целое число суток ≥ 1.",
        )
        await self._repository.get_or_create_default_settings(nmid=nmid)
        await self._repository.update_settings(
            nmid=nmid,
            retest_interval_days=parsed,
        )
        return await self.build_view(adv_setting_original_id)

    async def clear_shelf_exhausted_pause(
        self,
        adv_setting_original_id: int,
    ) -> bool:
        """Кнопка «Сбросить паузу»: clear только PG our-block (без forced start)."""
        adv = await self._get_adv_or_raise(adv_setting_original_id)
        nmid = self._get_single_nmid_or_raise(adv)
        return await self._repository.clear_shelf_exhausted_pause(nmid)

    async def set_strategy(
        self,
        adv_setting_original_id: int,
        strategy: AutoShelfBidControlStrategy,
    ) -> AutoShelfBidControlViewDTO:
        """Persist selected strategy without mutating the live WB bid."""
        adv = await self._get_adv_or_raise(adv_setting_original_id)
        normalized_strategy = (
            AutoShelfBidControlStrategy.CPC
            if strategy == AutoShelfBidControlStrategy.CYCLE_METRIC
            else strategy
        )
        adv = await self._repository.update_adv_strategy(
            adv_setting_original_id,
            normalized_strategy,
        )
        nmid = self._get_single_nmid_or_raise(adv)
        state = await self._repository.get_state(nmid)
        if state is None or state.current_mode != "main":
            return await self.build_view(adv_setting_original_id)
        # Strategy changes become visible in the UI immediately because
        # `build_view()` rebuilds the snapshot with the new mode. The actual
        # live bid is left for the next worker tick, which remains the single
        # authoritative writer for strategy-driven main-bid changes.
        return await self.build_view(adv_setting_original_id)

    async def reset_cycle(self, adv_setting_original_id: int) -> AutoShelfBidControlViewDTO:
        """Сбросить цикл в mode=test и выставить middle bid через setter."""
        adv = await self._get_adv_or_raise(adv_setting_original_id)
        nmid = self._get_single_nmid_or_raise(adv)
        settings_obj = await self._repository.get_or_create_default_settings(nmid=nmid)
        view = await self.build_view(adv_setting_original_id)
        min_bid = view.min_bid_minor
        if min_bid is None:
            raise AutoShelfBidControlTelegramError(
                "Нельзя сбросить цикл: минимальная ставка WB сейчас недоступна."
            )
        max_bid = int(settings_obj.max_bid_minor)
        if max_bid < int(min_bid):
            raise AutoShelfBidControlTelegramError(
                "Нельзя сбросить цикл: max ставка ниже минимальной ставки WB."
            )
        middle_bid = AutoShelfBidControlManager._middle_bid(int(min_bid), max_bid) # pyright: ignore
        self._require_bid_units_confirmed_for_manual_set()
        now = datetime.now(UTC)
        state = await self._repository.get_state(nmid)
        if state is None:
            state = await self._repository.build_state(
                nmid=nmid,
                currency=settings_obj.currency,
                current_mode="test",
                current_main_bid_minor=None,
                current_test_bid_minor=middle_bid,
                current_cycle_started_at=now,
                previous_cycle_started_at=None,
                main_started_at=None,
                test_started_at=now,
                last_reason="manual_cycle_reset",
            )
        else:
            state.previous_cycle_started_at = state.current_cycle_started_at
            state.current_cycle_started_at = now
            state.current_mode = "test"
            state.current_test_bid_minor = middle_bid
            state.test_started_at = now
            state.main_started_at = None
            state.last_reason = "manual_cycle_reset"
        _ = await self._repository.save_state(state)
        await self._set_bid(
            adv=adv,
            nmid=nmid,
            bid_minor=middle_bid,
            currency=settings_obj.currency,
        )
        return await self.build_view(adv_setting_original_id)

    async def force_main(self, adv_setting_original_id: int) -> AutoShelfBidControlViewDTO:
        """Принудительно перевести state в mode=main и выставить main bid."""
        adv = await self._get_adv_or_raise(adv_setting_original_id)
        nmid = self._get_single_nmid_or_raise(adv)
        state = await self._repository.get_state(nmid)
        if state is None:
            raise AutoShelfBidControlTelegramError(
                "Нельзя вернуть main-ставку: состояние ещё не создано."
            )
        current_main_bid_minor = state.current_main_bid_minor
        if current_main_bid_minor is None:
            raise AutoShelfBidControlTelegramError(
                "Нельзя вернуть main-ставку: рабочая ставка ещё не определена."
            )
        self._require_bid_units_confirmed_for_manual_set()
        settings_obj = await self._repository.get_or_create_default_settings(nmid=nmid)
        now = datetime.now(UTC)
        state.current_mode = "main"
        state.main_started_at = now
        state.last_reason = "manual_force_main"
        _ = await self._repository.save_state(state)
        await self._set_bid(
            adv=adv,
            nmid=nmid,
            bid_minor=int(current_main_bid_minor),
            currency=settings_obj.currency,
        )
        return await self.build_view(adv_setting_original_id)

    @staticmethod
    def _require_bid_units_confirmed_for_manual_set() -> None:
        """Запретить ручной PATCH WB-ставки, пока gate единиц ставок не подтверждён."""
        if not settings.AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED:
            raise AutoShelfBidControlTelegramError(_BID_UNITS_GATE_ERROR)

    @staticmethod
    def _parse_positive_int(value: str, error_message: str) -> int:
        text = value.strip()
        if not text.isdigit():
            raise AutoShelfBidControlTelegramError(error_message)
        parsed = int(text)
        if parsed <= 0:
            raise AutoShelfBidControlTelegramError(error_message)
        return parsed

    @staticmethod
    def _parse_test_share(value: str) -> float:
        text = value.strip().replace(",", ".")
        try:
            parsed = float(text)
        except ValueError as exc:
            raise AutoShelfBidControlTelegramError(
                "Доля теста должна быть больше 0 и не больше 49%."
            ) from exc
        if parsed > 1:
            parsed = parsed / 100
        if parsed <= 0 or parsed > 0.49:
            raise AutoShelfBidControlTelegramError(
                "Доля теста должна быть больше 0 и не больше 49%."
            )
        return float(parsed)

    async def _get_adv_or_raise(self, adv_setting_original_id: int) -> AdvSetting:
        adv = await self._repository.get_adv_setting_by_original_id(adv_setting_original_id)
        if adv is None:
            raise AutoShelfBidControlTelegramError("Настройка кампании не найдена.")
        return adv

    @staticmethod
    def _get_single_nmid_or_raise(adv: AdvSetting) -> int:
        nmids = sorted(int(x) for x in (adv.nmids or []))
        if len(nmids) != 1:
            raise AutoShelfBidControlTelegramError(
                "Управление ставкой в полках доступно только для Auto-РК с одним артикулом. "
                "В этой РК несколько nmID, модуль не включён."
            )
        return int(nmids[0])

    async def _set_bid(
        self,
        *,
        adv: AdvSetting,
        nmid: int,
        bid_minor: int,
        currency: str,
    ) -> None:
        """PATCH ставки WB внутри ``DIManager.create`` (до ``shutdown_resources``)."""
        from app.core.di.app_container import AppContainer
        from app.core.di.di_manager import DIManager

        shop_id = adv.wb_cabinet.shop_id
        complex_adv_like = cast(
            ComplexAdv,
            type(
                "_TelegramComplexAdv",
                (),
                {"auto_adv_id": int(adv.adv_id), "nmids": [int(nmid)]},
            )(),
        )
        async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
            typed_container = cast(_DIContainerProtocol, container)
            factory = (
                typed_container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
            )
            hub = factory.get_wb_manager_hub(shop_id)
            setter = AutoShelfBidSetter(
                cast(WBModifier, hub.wb_modifier),
                bid_cache_manager=self._bid_cache,
            )
            await setter.set_bid(
                complex_adv_like,
                bid_minor=int(bid_minor),
                currency=currency,
            )
