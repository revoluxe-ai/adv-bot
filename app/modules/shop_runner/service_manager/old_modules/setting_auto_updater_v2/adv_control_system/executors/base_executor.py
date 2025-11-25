"""Базовый интерфейс исполнителя для реактивной системы управления РК."""

from abc import ABC, abstractmethod

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    ExecutionResult,
    PipelineContext,
)


class BaseExecutor(ABC):
    """Базовый интерфейс исполнителя adv."""

    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> ExecutionResult:
        """Выполняет одно действие над кампанией.

        Args:
            ctx: Контекст выполнения с данными кампании, ключевыми словами,
                 планом, фактом, сессией БД, состоянием и силой реакции

        Returns:
            ExecutionResult с результатом выполнения:
                - success: удалось ли выполнить действие
                - efficiency: насколько действие приблизило к цели (0.0-1.0)
                - used_power: сколько силы было использовано
        """
        ...
