import logging
from typing import Optional

from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.dto.plan_fact_stat_dto import PlanFactStatDTO

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.pre_complex_adv import (
    PreComplexAdv,
)

logger = logging.getLogger(__name__)


class PlanFactController:
    """Контроллер для обработки план-факта данных одной кампании"""


    @staticmethod
    async def get_plan_fact_dto(adv: ComplexAdv) -> PlanFactStatDTO:
        # Получаем план данные (синхронно)
        plan: Optional[PlanData] = PlanFactProvider.get_plan_data(
            adv.adv_setting
        )
        keywords = await adv.get_keywords()
        provider = PlanFactProvider(adv.adv_setting)
        stat = await provider.get_stat_data(keywords)
        fact = await provider.get_fact_data(stat)

        # Создаем DTO
        dto = PlanFactStatDTO.create(
            adv_id=adv.adv_id,
            shop_id=adv.shop_id,
            plan=plan,
            fact=fact,
        )
        return dto


    @staticmethod
    async def _resolve_fact_for_pre_adv(
        pre_adv: PreComplexAdv,
    ) -> FactData:
        from app.modules.shop_runner.required_data_miss import (
            fetch_calculated_keywords_from_redis,
        )

        shop_id = pre_adv.auto_adv.wb_cabinet.shop_id
        adv_id = pre_adv.adv_id
        cached_keywords = await fetch_calculated_keywords_from_redis(
            adv_id,
            shop_id=shop_id,
        )
        assert cached_keywords is not None
        keywords = sorted(
            cached_keywords,
            key=lambda kw: kw.rating or 0,
            reverse=True,
        )
        provider = PlanFactProvider(pre_adv.auto_adv)
        stat = await provider.get_stat_data(keywords)
        fact = await provider.get_fact_data(stat)
        return fact

    @staticmethod
    async def process_adv(
        adv: ComplexAdv, version: float
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
        provider = PlanFactProvider(adv.adv_setting)
        stat = await provider.get_stat_data(keywords)
        fact = await provider.get_fact_data(stat)

        # Создаем DTO
        dto = PlanFactStatDTO.create(
            adv_id=adv.adv_id,
            shop_id=adv.shop_id,
            plan=plan,
            fact=fact,
            version=version,
        )
        return dto

    @staticmethod
    async def process_pre_adv(
        pre_adv: PreComplexAdv,
        version: float,
    ) -> PlanFactStatDTO | None:
        fact = await PlanFactController._resolve_fact_for_pre_adv(pre_adv)
        return PlanFactStatDTO.create(
            adv_id=pre_adv.adv_id,
            shop_id=pre_adv.auto_adv.wb_cabinet.shop_id,
            plan=pre_adv.plan_data,
            fact=fact,
            version=version,
        )










