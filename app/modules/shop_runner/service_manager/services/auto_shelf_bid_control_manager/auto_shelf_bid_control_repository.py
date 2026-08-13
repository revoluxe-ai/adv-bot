"""Repository состояния/настроек Auto Shelf Bid Control в PostgreSQL."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import joinedload

from app.modules.common_slaves.wildberries.models.auto_shelf_bid_control import (
    AutoShelfBidControlSettings,
    AutoShelfBidControlState,
)
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as get_session_maker

from .bid_units import DEFAULT_MAX_BID_MINOR, DEFAULT_MIN_BID_DISTANCE_MINOR
from .settings_normalizer import compute_settings_repair

DEFAULT_CURRENCY = "RUB"
DEFAULT_TARGET_TEST_IMPRESSIONS = 500
DEFAULT_TARGET_TEST_OBSERVATION_MINUTES = 60
DEFAULT_TEST_SHARE = 0.1
DEFAULT_RETEST_INTERVAL_DAYS = 7

# Product-дефолты при автосоздании settings (get_or_create_default_settings).
# Все *_minor — копейки (см. bid_units.py); Telegram вводит рубли.


class AutoShelfBidControlRepository:
    """Чтение/запись настроек и состояния control-модуля."""

    async def get_settings(self, nmid: int) -> AutoShelfBidControlSettings | None:
        """Вернуть настройки control для nmid."""
        async with get_session_maker(read_only=True) as session:
            stmt: Select[tuple[AutoShelfBidControlSettings]] = select(
                AutoShelfBidControlSettings
            ).where(AutoShelfBidControlSettings.nmid == nmid)
            return (await session.execute(stmt)).scalar_one_or_none()

    async def get_state(self, nmid: int) -> AutoShelfBidControlState | None:
        """Вернуть state control для nmid."""
        async with get_session_maker(read_only=True) as session:
            stmt: Select[tuple[AutoShelfBidControlState]] = select(
                AutoShelfBidControlState
            ).where(AutoShelfBidControlState.nmid == nmid)
            return (await session.execute(stmt)).scalar_one_or_none()

    async def get_or_create_settings(
        self,
        nmid: int,
        default_max_bid_minor: int,
        currency: str = "RUB",
    ) -> AutoShelfBidControlSettings:
        """Вернуть существующие settings или создать default-настройки для nmid."""
        async with get_session_maker() as session:
            stmt: Select[tuple[AutoShelfBidControlSettings]] = select(
                AutoShelfBidControlSettings
            ).where(AutoShelfBidControlSettings.nmid == nmid)
            settings_obj = (await session.execute(stmt)).scalar_one_or_none()
            if settings_obj is not None:
                return settings_obj
            created = AutoShelfBidControlSettings(
                nmid=nmid,
                max_bid_minor=int(default_max_bid_minor),
                currency=currency,
                min_bid_distance_minor=DEFAULT_MIN_BID_DISTANCE_MINOR,
                target_test_impressions=DEFAULT_TARGET_TEST_IMPRESSIONS,
                target_test_observation_minutes=DEFAULT_TARGET_TEST_OBSERVATION_MINUTES,
                test_share=DEFAULT_TEST_SHARE,
                retest_interval_days=DEFAULT_RETEST_INTERVAL_DAYS,
            )
            session.add(created)
            await session.flush()
            await session.refresh(created)
            await session.commit()
            return created

    async def get_or_create_default_settings(
        self,
        nmid: int,
    ) -> AutoShelfBidControlSettings:
        """Вернуть settings для nmid или создать строку с product-дефолтами.

        Дефолты:
            max_bid_minor=50000, currency=RUB, min_bid_distance_minor=100,
            target_test_impressions=500, test_share=0.1.

        Dry-run задаётся глобально через AUTO_SHELF_BID_CONTROL_DRY_RUN.
        Единицы ставок — identity (как в AutoShelfBidSetter), без умножения на 100.
        """
        return await self.get_or_create_settings(
            nmid=nmid,
            default_max_bid_minor=DEFAULT_MAX_BID_MINOR,
            currency=DEFAULT_CURRENCY,
        )

    async def save_settings(
        self,
        settings_obj: AutoShelfBidControlSettings,
    ) -> AutoShelfBidControlSettings:
        """Сохранить settings в БД (insert/update)."""
        async with get_session_maker(read_only=False) as session:
            session.add(settings_obj)
            await session.flush()
            await session.refresh(settings_obj)
            await session.commit()
            return settings_obj

    async def repair_settings_units(
        self,
        nmid: int,
        *,
        min_bid_minor: int,
        actual_bid_minor: int | None,
    ) -> AutoShelfBidControlSettings:
        """Исправить legacy max/шаг в копейках и сохранить, если нужно."""
        settings_obj = await self.get_settings(nmid)
        if settings_obj is None:
            raise ValueError("settings_not_found")
        repair = compute_settings_repair(
            settings_obj,
            min_bid_minor=min_bid_minor,
            actual_bid_minor=actual_bid_minor,
        )
        if not repair.changed:
            return settings_obj
        return await self.update_settings(
            nmid=nmid,
            max_bid_minor=repair.max_bid_minor,
            min_bid_distance_minor=repair.min_bid_distance_minor,
        )

    async def update_settings(
        self,
        nmid: int,
        *,
        max_bid_minor: int | None = None,
        test_share: float | None = None,
        target_test_impressions: int | None = None,
        target_test_observation_minutes: int | None = None,
        min_bid_distance_minor: int | None = None,
        retest_interval_days: int | None = None,
    ) -> AutoShelfBidControlSettings:
        """Обновить отдельные поля settings по nmid."""
        async with get_session_maker(read_only=False) as session:
            stmt: Select[tuple[AutoShelfBidControlSettings]] = select(
                AutoShelfBidControlSettings
            ).where(AutoShelfBidControlSettings.nmid == nmid)
            settings_obj = (await session.execute(stmt)).scalar_one_or_none()
            if settings_obj is None:
                raise ValueError("settings_not_found")
            if max_bid_minor is not None:
                settings_obj.max_bid_minor = int(max_bid_minor)
            if test_share is not None:
                settings_obj.test_share = float(test_share)
            if target_test_impressions is not None:
                settings_obj.target_test_impressions = int(target_test_impressions)
            if target_test_observation_minutes is not None:
                settings_obj.target_test_observation_minutes = int(
                    target_test_observation_minutes
                )
            if min_bid_distance_minor is not None:
                settings_obj.min_bid_distance_minor = int(min_bid_distance_minor)
            if retest_interval_days is not None:
                settings_obj.retest_interval_days = int(retest_interval_days)
            await session.flush()
            await session.refresh(settings_obj)
            await session.commit()
            return settings_obj

    async def set_enabled(
        self,
        adv_setting_original_id: int,
        enabled: bool,
    ) -> None:
        """Включить/выключить control-флаг для AdvSetting."""
        async with get_session_maker() as session:
            stmt: Select[tuple[AdvSetting]] = select(AdvSetting).where(
                AdvSetting.id == adv_setting_original_id
            )
            adv = (await session.execute(stmt)).scalar_one_or_none()
            if adv is None:
                raise ValueError("adv_setting_not_found")
            adv.auto_shelf_bid_control_enabled = bool(enabled)
            await session.flush()
            await session.commit()
            return None

    async def update_adv_strategy(
        self,
        adv_setting_original_id: int,
        strategy: AutoShelfBidControlStrategy,
    ) -> AdvSetting:
        """Update the main-bid strategy on AdvSetting and return fresh model."""
        async with get_session_maker() as session:
            stmt: Select[tuple[AdvSetting]] = (
                select(AdvSetting)
                .options(joinedload(AdvSetting.wb_cabinet))
                .where(AdvSetting.id == adv_setting_original_id)
            )
            adv = (await session.execute(stmt)).scalar_one_or_none()
            if adv is None:
                raise ValueError("adv_setting_not_found")
            adv.auto_shelf_bid_control_strategy = strategy
            await session.flush()
            await session.refresh(adv)
            await session.commit()
            return adv

    async def save_state(self, state: AutoShelfBidControlState) -> AutoShelfBidControlState:
        """Создать или обновить state в БД."""
        async with get_session_maker() as session:
            existing_stmt: Select[tuple[AutoShelfBidControlState]] = select(
                AutoShelfBidControlState
            ).where(AutoShelfBidControlState.nmid == state.nmid)
            existing = (await session.execute(existing_stmt)).scalar_one_or_none()
            if existing is None:
                session.add(state)
                await session.flush()
                await session.refresh(state)
                await session.commit()
                return state

            existing.current_mode = state.current_mode
            existing.current_main_bid_minor = state.current_main_bid_minor
            existing.current_test_bid_minor = state.current_test_bid_minor
            existing.currency = state.currency
            existing.current_cycle_started_at = state.current_cycle_started_at
            existing.previous_cycle_started_at = state.previous_cycle_started_at
            existing.main_started_at = state.main_started_at
            existing.test_started_at = state.test_started_at
            existing.last_reason = state.last_reason
            existing.shelf_exhausted_pause_active = bool(
                state.shelf_exhausted_pause_active
            )
            existing.shelf_exhausted_paused_at = state.shelf_exhausted_paused_at
            existing.shelf_exhausted_due_at = state.shelf_exhausted_due_at
            existing.shelf_exhausted_epoch_start = state.shelf_exhausted_epoch_start
            existing.shelf_exhausted_resolve_cpo_kind = (
                state.shelf_exhausted_resolve_cpo_kind
            )
            existing.shelf_exhausted_resolve_cpo_value = (
                state.shelf_exhausted_resolve_cpo_value
            )
            existing.shelf_exhausted_notify_sent_at = (
                state.shelf_exhausted_notify_sent_at
            )
            existing.shelf_exhausted_epoch_pending = bool(
                state.shelf_exhausted_epoch_pending
            )
            await session.flush()
            await session.refresh(existing)
            await session.commit()
            return existing

    async def latch_shelf_exhausted_pause(
        self,
        nmid: int,
        *,
        now: datetime,
        due_at: datetime,
        resolve_cpo_kind: str,
        resolve_cpo_value: float,
    ) -> AutoShelfBidControlState | None:
        """Записать PG our-block + recorded resolve CPO (canonical SoT).

        Не вызывает WB pause — это ownership activity-control.
        """
        async with get_session_maker(read_only=False) as session:
            stmt: Select[tuple[AutoShelfBidControlState]] = select(
                AutoShelfBidControlState
            ).where(AutoShelfBidControlState.nmid == nmid)
            state = (await session.execute(stmt)).scalar_one_or_none()
            if state is None:
                return None
            state.shelf_exhausted_pause_active = True
            state.shelf_exhausted_paused_at = now
            state.shelf_exhausted_due_at = due_at
            state.shelf_exhausted_resolve_cpo_kind = resolve_cpo_kind
            state.shelf_exhausted_resolve_cpo_value = float(resolve_cpo_value)
            await session.flush()
            await session.refresh(state)
            await session.commit()
            return state

    async def clear_shelf_exhausted_pause(
        self,
        nmid: int,
    ) -> bool:
        """Снять только наш PG our-block (без forced Auto start / epoch).

        Сбрасывает enter-scoped notify latch
        (``shelf_exhausted_notify_sent_at``), чтобы следующий вход в
        shelf-exhausted pause снова мог отправить paid Telegram notify.
        Resolve CPO / ``epoch_start`` оставляем для аудита; ``epoch_start``
        обновляется только при реальном Auto start.

        Returns:
            True если блок был активен и снят; False если нечего снимать.
        """
        async with get_session_maker(read_only=False) as session:
            stmt: Select[tuple[AutoShelfBidControlState]] = select(
                AutoShelfBidControlState
            ).where(AutoShelfBidControlState.nmid == nmid)
            state = (await session.execute(stmt)).scalar_one_or_none()
            if state is None or not bool(state.shelf_exhausted_pause_active):
                return False
            state.shelf_exhausted_pause_active = False
            state.shelf_exhausted_paused_at = None
            state.shelf_exhausted_due_at = None
            state.shelf_exhausted_epoch_pending = True
            # Enter-scoped UX latch: clear ends the pause episode, so the next
            # enter must be allowed to notify again (once-per-enter dedupe).
            state.shelf_exhausted_notify_sent_at = None
            # resolve / epoch_start оставляем для аудита;
            # epoch_start обновляется только при реальном Auto start.
            await session.flush()
            await session.commit()
            return True

    async def mark_shelf_exhausted_epoch_started(
        self,
        nmid: int,
        *,
        epoch_start: datetime,
    ) -> None:
        """Зафиксировать epoch_start после реального Auto start (consume pending)."""
        async with get_session_maker(read_only=False) as session:
            stmt: Select[tuple[AutoShelfBidControlState]] = select(
                AutoShelfBidControlState
            ).where(AutoShelfBidControlState.nmid == nmid)
            state = (await session.execute(stmt)).scalar_one_or_none()
            if state is None:
                return None
            state.shelf_exhausted_epoch_start = epoch_start
            state.shelf_exhausted_epoch_pending = False
            await session.flush()
            await session.commit()
            return None

    async def mark_shelf_exhausted_notify_sent(
        self,
        nmid: int,
        *,
        sent_at: datetime,
    ) -> None:
        """Дедуп paid notify: зафиксировать момент отправки."""
        async with get_session_maker(read_only=False) as session:
            stmt: Select[tuple[AutoShelfBidControlState]] = select(
                AutoShelfBidControlState
            ).where(AutoShelfBidControlState.nmid == nmid)
            state = (await session.execute(stmt)).scalar_one_or_none()
            if state is None:
                return None
            state.shelf_exhausted_notify_sent_at = sent_at
            await session.flush()
            await session.commit()
            return None

    async def is_control_enabled_for_nmid(self, nmid: int) -> bool:
        """Проверить, что у nmid включен control-флаг в AdvSetting."""
        async with get_session_maker(read_only=True) as session:
            stmt: Select[tuple[int]] = (
                select(AdvSetting.id)
                .where(
                    AdvSetting.auto_shelf_bid_control_enabled.is_(True),
                    AdvSetting.nmids.contains([nmid]),
                )
                .limit(1)
            )
            row = (await session.execute(stmt)).first()
            return row is not None

    async def get_mode_for_nmid(self, nmid: int) -> str:
        """Mode для записи в CH: метка сегмента инкремента, не «фаза UI».

        - control выключен → ``test`` (пассивный сбор по текущей ставке WB);
        - control включен, state нет → ``test`` (до первого тика control);
        - control включен, state есть → ``state.current_mode`` (test/main цикл).

        Аналитика «покрытых ставок» и прогресс test по ``bid_minor`` читают все mode
        (в т.ч. legacy ``main`` на той же ставке), см. analytics_repository.
        """
        enabled = await self.is_control_enabled_for_nmid(nmid)
        if not enabled:
            return "test"
        state = await self.get_state(nmid)
        if state is None:
            return "test"
        mode = state.current_mode
        if mode not in {"main", "test"}:
            return "main"
        return mode

    async def build_state(
        self,
        *,
        nmid: int,
        currency: str,
        current_mode: str,
        current_main_bid_minor: int | None,
        current_test_bid_minor: int | None,
        current_cycle_started_at: datetime,
        previous_cycle_started_at: datetime | None,
        main_started_at: datetime | None,
        test_started_at: datetime | None,
        last_reason: str,
    ) -> AutoShelfBidControlState:
        """Сконструировать state-объект перед сохранением."""
        return AutoShelfBidControlState(
            nmid=nmid,
            currency=currency,
            current_mode=current_mode,
            current_main_bid_minor=current_main_bid_minor,
            current_test_bid_minor=current_test_bid_minor,
            current_cycle_started_at=current_cycle_started_at,
            previous_cycle_started_at=previous_cycle_started_at,
            main_started_at=main_started_at,
            test_started_at=test_started_at,
            last_reason=last_reason,
        )

    async def get_adv_setting_by_original_id(self, adv_setting_original_id: int) -> AdvSetting | None:
        """Получить AdvSetting по id для Telegram (с wb_cabinet для WB API)."""
        async with get_session_maker(read_only=True) as session:
            stmt: Select[tuple[AdvSetting]] = (
                select(AdvSetting)
                .options(joinedload(AdvSetting.wb_cabinet))
                .where(AdvSetting.id == adv_setting_original_id)
            )
            return (await session.execute(stmt)).scalar_one_or_none()

    async def update_state_reason(self, nmid: int, reason: str) -> None:
        """Обновить только last_reason для существующего состояния."""
        async with get_session_maker() as session:
            stmt: Select[tuple[AutoShelfBidControlState]] = select(
                AutoShelfBidControlState
            ).where(AutoShelfBidControlState.nmid == nmid)
            state = (await session.execute(stmt)).scalar_one_or_none()
            if state is None:
                return None
            state.last_reason = reason
            await session.flush()
            await session.commit()
            return None
