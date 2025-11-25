"""Структуры данных для реактивной системы управления РК."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
import typing

if typing.TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
        ComplexAdv,
    )
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)


@dataclass
class ForceContext:
    """Сила реакции adv-управления (на первом этапе всегда = 1)."""

    value: float

    def weaken(self, efficiency: float) -> "ForceContext":
        """Ослабляет силу с учётом эффективности исполнителя.

        Args:
            efficiency: Эффективность исполнителя (0.0-1.0)

        Returns:
            Новый ForceContext с ослабленной силой
        """
        new_value = self.value - efficiency
        if new_value < 0:
            new_value = 0
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

    complex_adv: "ComplexAdv"
    plan: PlanData
    fact: FactData
    session: AsyncSession
    state: SalesStates
    force: ForceContext


# TODO: Внедрить лимит обращений в поддержку
# TODO: Вывести в боте информацию о Среднем  CTR Авто за два дня
# TODO: Вывести в боте информацию о себестоимости заказов в Авто, Аукционе
