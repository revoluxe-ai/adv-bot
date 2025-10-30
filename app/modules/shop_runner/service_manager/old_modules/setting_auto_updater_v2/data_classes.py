"""Структуры данных для реактивной системы управления РК."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.sales_state.sales_states import (
    SalesStates,
)


@dataclass
class ForceContext:
    """Сила реакции adv-управления (на первом этапе всегда = 1)."""

    value: int

    def weaken(self, efficiency: float) -> "ForceContext":
        """Ослабляет силу с учётом эффективности исполнителя.
        
        Args:
            efficiency: Эффективность исполнителя (0.0-1.0)
            
        Returns:
            Новый ForceContext с ослабленной силой
        """
        new_value = max(0, int(self.value * (1 - efficiency)))
        return ForceContext(value=new_value)


@dataclass
class ExecutionResult:
    """Результат выполнения исполнителя."""

    success: bool  # Удалось ли выполнить действие
    efficiency: float  # 0.0–1.0, насколько действие приблизило кампанию к цели
    used_power: int  # Сколько силы было использовано


@dataclass
class PipelineContext:
    """Контекст исполнения каскада действий для одной кампании (adv)."""

    adv: AdvSetting
    keywords: list[CalculatedKeyword]
    plan: PlanData
    fact: FactData
    session: AsyncSession
    state: SalesStates
    force: ForceContext

