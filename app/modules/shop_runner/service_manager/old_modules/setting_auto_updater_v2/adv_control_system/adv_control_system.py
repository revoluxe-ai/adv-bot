"""Главный оркестратор реактивной системы управления РК."""

# TODO: перенести Harbor на нормальный домен
# TODO: Подключить оплату через бот
# TODO: Сделать сайт + воронка
# TODO Система автоматизации проверки ключей на релевантность
# TODO: Усилить правила
# TODO: Добавить новые исполнители в обновление параметров
# TODO: Вывестив  систему платные консультации и обучение
# TODO: Настроить мощность исполнителям

import logging

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.plan_fact_change_redis_caches import (
    ChangePlanFact,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.setting_auto_updater import (
    AdvSettingAutoUpdater,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import (
    ComplexAdv,
)
from .data_classes.data_classes import ForceContext, PipelineContext
from .sales_state.sales_states import SalesStates, detect_campaign_state
from .planners.scenario_planner import ScenarioPlanner
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


class AdvControlSystem:
    """Главный управляющий модуль кампаний adv.

    Реализует реактивную систему управления:
    1. Определяет состояние кампании (OVERSPEND, UNDERPERFORM, STABLE, OPTIMAL)
    2. Устанавливает силу реакции (на первом этапе всегда = 1)
    3. Запускает соответствующую цепочку исполнителей
    """

    def __init__(self, max_last_period: int = 2):
        """
        Args:
            max_last_period: Количество дней для анализа статистики
        """
        self.max_last_period = max_last_period
        self.planner = ScenarioPlanner()

    async def process_adv(self, complex_adv: ComplexAdv, force: float = 1) -> None:

        keywords = await complex_adv.get_keywords()
        adv = complex_adv.adv_setting
        # 2. Получаем план
        plan = AdvSettingAutoUpdater.get_plan_data(adv)
        if not plan:
            logger.debug(
                "[adv_id=%s] План не установлен, пропускаем обработку", adv.adv_id
            )
            return

        # 3. Получаем факт
        updater = AdvSettingAutoUpdater(adv, self.max_last_period)
        fact = await updater.get_fact_data(keywords)

        # 3.1. Проверяем, изменились ли план и факт с прошлого раза
        plan_fact_change = ChangePlanFact(adv)
        if await plan_fact_change.check_equal_in_cache(plan, fact):
            logger.debug(
                "[adv_id=%s] План и факт не изменились с прошлого раза, пропускаем",
                adv.adv_id,
            )
            return

        # 4. Определяем состояние
        state = detect_campaign_state(plan, fact)

        if state is None:
            logger.info(
                "[adv_id=%s] Недостаточно данных для определения состояния", adv.adv_id
            )
            return

        if state == SalesStates.OPTIMAL:
            logger.info(
                "[adv_id=%s] Состояние OPTIMAL — действий не требуется", adv.adv_id
            )
            return

        force_obj = ForceContext(value=force)

        logger.debug(
            "[adv_id=%s] Состояние: %s, plan_orders=%s, fact_orders=%.1f, target_pay=%s, max_pay=%s, fact_pay=%.1f",
            adv.adv_id,
            state.name,
            plan.orders,
            fact.predict_orders,
            plan.target_pay_for_order,
            plan.max_pay_for_order,
            fact.pay_for_order,
        )

        # 6. Создаём контекст и запускаем сценарий
        async with sm() as session:
            ctx = PipelineContext(
                complex_adv=complex_adv,
                plan=plan,
                fact=fact,
                session=session,
                state=state,
                force=force_obj,
            )

            await self.planner.run_for_state(ctx)
            await session.commit()

        # 7. Сохраняем новое состояние план-факт
        await plan_fact_change.set_new_plan_fact(plan, fact)
