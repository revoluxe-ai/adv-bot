"""Сервис Telegram-действий для управления ставкой полок Auto-РК."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models.models import AdvSetting

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)

from .auto_shelf_bid_control_repository import AutoShelfBidControlRepository
from .auto_shelf_bid_control_view_provider import AutoShelfBidControlViewProvider
from .auto_shelf_bid_setter import AutoShelfBidSetter
from .bid_units import format_bid_minor_for_telegram, rubles_to_bid_minor
from .dto import AutoShelfBidControlViewDTO


@dataclass(slots=True)
class AutoShelfBidControlTelegramError(Exception):
    """Пользовательская ошибка сценария Telegram-управления."""

    message: str


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

    async def enable(self, adv_setting_original_id: int) -> AutoShelfBidControlViewDTO:
        """Включить управление ставкой; при отсутствии settings создать default."""
        adv = await self._get_adv_or_raise(adv_setting_original_id)
        nmid = self._get_single_nmid_or_raise(adv)
        await self._repository.get_or_create_default_settings(nmid=nmid)
        if adv.adv_id is not None:
            view_before = await self.build_view(adv_setting_original_id)
            actual = view_before.actual_bid_minor
            max_bid = view_before.max_bid_minor
            # build_view мог записать legacy repair в БД — берём max из view, не stale settings.
            if (
                actual is not None
                and max_bid is not None
                and int(max_bid) < int(actual)
            ):
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
        if view.min_bid_minor is not None and parsed < int(view.min_bid_minor):
            raise AutoShelfBidControlTelegramError(
                "Максимальная ставка не может быть ниже минимальной ставки WB: "
                f"{format_bid_minor_for_telegram(view.min_bid_minor, view.currency)}"
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
        middle_bid = int(round((int(min_bid) + max_bid) / 2))
        now = datetime.now(timezone.utc)
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
        if state.current_main_bid_minor is None:
            raise AutoShelfBidControlTelegramError(
                "Нельзя вернуть main-ставку: рабочая ставка ещё не определена."
            )
        settings_obj = await self._repository.get_or_create_default_settings(nmid=nmid)
        now = datetime.now(timezone.utc)
        state.current_mode = "main"
        state.main_started_at = now
        state.last_reason = "manual_force_main"
        _ = await self._repository.save_state(state)
        await self._set_bid(
            adv=adv,
            nmid=nmid,
            bid_minor=int(state.current_main_bid_minor),
            currency=settings_obj.currency,
        )
        return await self.build_view(adv_setting_original_id)

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
        if adv.adv_id is None:
            raise AutoShelfBidControlTelegramError(
                "Нельзя выставить ставку: у кампании отсутствует Auto РК id."
            )
        from app.core.di.app_container import AppContainer
        from app.core.di.di_manager import DIManager

        shop_id = adv.wb_cabinet.shop_id
        async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
            factory = (
                container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
            )
            hub = factory.get_wb_manager_hub(shop_id)
            setter = AutoShelfBidSetter(
                hub.wb_modifier,
                bid_cache_manager=self._bid_cache,
            )
        complex_adv_like = SimpleNamespace(auto_adv_id=int(adv.adv_id), nmids=[int(nmid)])
        await setter.set_bid(
            complex_adv_like,
            bid_minor=int(bid_minor),
            currency=currency,
        )
