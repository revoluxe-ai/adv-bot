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
from collections.abc import Awaitable

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.plan_fact_change_redis_caches import (
    ChangePlanFact,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.setting_auto_updater import (
    AdvSettingAutoUpdater,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
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

    async def process_adv(self, complex_adv: ComplexAdv) -> None:

        keywords = await complex_adv.keywords_coro
        adv = complex_adv.adv_setting
        # 2. Получаем план
        plan = AdvSettingAutoUpdater.get_plan_data(adv)
        if not plan:
            logger.debug(
                f"[adv_id={adv.adv_id}] План не установлен, пропускаем обработку"
            )
            return

        # 3. Получаем факт
        updater = AdvSettingAutoUpdater(adv, self.max_last_period)
        fact = await updater.get_fact_data(keywords)

        # 3.1. Проверяем, изменились ли план и факт с прошлого раза
        plan_fact_change = ChangePlanFact(adv)
        if await plan_fact_change.check_equal_in_cache(plan, fact):
            logger.debug(
                f"[adv_id={adv.adv_id}] План и факт не изменились с прошлого раза, пропускаем"
            )
            return

        # 4. Определяем состояние
        state = detect_campaign_state(plan, fact)

        if state is None:
            logger.info(
                f"[adv_id={adv.adv_id}] Недостаточно данных для определения состояния"
            )
            return

        if state == SalesStates.OPTIMAL:
            logger.info(
                f"[adv_id={adv.adv_id}] Состояние OPTIMAL — действий не требуется"
            )
            return

        # 5. Устанавливаем силу реакции (на первом этапе всегда = 1)
        force = ForceContext(value=3)

        logger.debug(
            f"[adv_id={adv.adv_id}] Состояние: {state.name}, "
            f"plan_orders={plan.orders}, fact_orders={fact.predict_orders:.1f}, "
            f"target_pay={plan.target_pay_for_order}, max_pay={plan.max_pay_for_order}, "
            f"fact_pay={fact.pay_for_order:.1f}"
        )

        # 6. Создаём контекст и запускаем сценарий
        async with sm() as session:
            ctx = PipelineContext(
                adv=adv,
                keywords=keywords,
                plan=plan,
                fact=fact,
                session=session,
                state=state,
                force=force,
            )

            await self.planner.run_for_state(ctx)

        # 7. Сохраняем новое состояние план-факт
        await plan_fact_change.set_new_plan_fact(plan, fact)
