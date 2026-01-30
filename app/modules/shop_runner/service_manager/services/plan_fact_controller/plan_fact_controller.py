import logging
from typing import Optional

from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    PlanData,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.dto.plan_fact_stat_dto import PlanFactStatDTO

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.fact_data_cache import FactDataCache, get_fact_data_for_adv

logger = logging.getLogger(__name__)


class PlanFactController:
    """Контроллер для обработки план-факта данных одной кампании"""


    @staticmethod
    async def get_plan_fact_dto(
        adv: ComplexAdv,
        fact_data_cache: FactDataCache | None = None,
    ) -> PlanFactStatDTO:
        # Получаем план данные (синхронно)
        plan: Optional[PlanData] = PlanFactProvider.get_plan_data(
            adv.adv_setting
        )
        keywords = await adv.get_keywords()
        fact = await get_fact_data_for_adv(
            adv,
            keywords=keywords,
            cache=fact_data_cache,
        )

        # Создаем DTO
        dto = PlanFactStatDTO.create(
            adv_id=adv.adv_id,
            shop_id=adv.shop_id,
            plan=plan,
            fact=fact,
        )
        return dto


    @staticmethod
    async def process_adv(
        adv: ComplexAdv,
        version: float,
        fact_data_cache: FactDataCache | None = None,
    ) -> PlanFactStatDTO | None:
        """
        Обрабатывает одну кампанию: получает план, факт и создает DTO.

        Args:
            adv: Объект ComplexAdv с данными кампании
            version: Версия для записи в ClickHouse

        Returns:
            PlanFactStatDTO или None, если не удалось получить данные
        """
        # Получаем план данные (синхронно)
        plan: Optional[PlanData] = PlanFactProvider.get_plan_data(
            adv.adv_setting
        )
        keywords = await adv.get_keywords()
        fact = await get_fact_data_for_adv(
            adv,
            keywords=keywords,
            cache=fact_data_cache,
        )

        # Создаем DTO
        dto = PlanFactStatDTO.create(
            adv_id=adv.adv_id,
            shop_id=adv.shop_id,
            plan=plan,
            fact=fact,
            version=version,
        )
        return dto







