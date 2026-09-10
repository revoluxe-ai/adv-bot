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
    ) -> FactData | None:
        """Факт для записи plan_fact_stats: keywords из Redis, без CH-пересчёта.

        При miss ``calculated_keywords`` — fallback на последний ``PlanFactSummary``
        из CH (уже в ``pre_adv``), иначе ``None`` (кампания пропускается в tick).
        Исключение не пробрасывается: batch plan-fact не должен падать из-за одной РК.
        """
        from app.modules.shop_runner.required_data_miss import (
            ShopRunnerKeywordsCacheMissError,
            fetch_calculated_keywords_from_redis,
        )
        from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
            fact_data_from_plan_fact_summary,
        )

        shop_id = pre_adv.auto_adv.wb_cabinet.shop_id
        adv_id = pre_adv.adv_id
        try:
            cached_keywords = await fetch_calculated_keywords_from_redis(
                adv_id,
                shop_id=shop_id,
            )
        except ShopRunnerKeywordsCacheMissError:
            logger.warning(
                "plan_fact: keywords cache miss adv_id=%s shop_id=%s; "
                "fallback plan_fact_summary или пропуск",
                adv_id,
                shop_id,
            )
            return fact_data_from_plan_fact_summary(
                pre_adv.plan_fact_summary,
                pre_adv.auto_adv,
            )

        keywords = sorted(
            cached_keywords,
            key=lambda kw: kw.rating or 0,
            reverse=True,
        )
        provider = PlanFactProvider(pre_adv.auto_adv)
        stat = await provider.get_stat_data(keywords)
        return await provider.get_fact_data(stat)

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
        """Обрабатывает pre-complex кампанию: план из base Plan, факт из Redis/summary.

        ``PreComplexAdv.plan_data`` может содержать overlay Plan для runtime-потребителей;
        в ClickHouse сохраняется только base Plan через ``PlanFactProvider.get_plan_data``.
        ``PreComplexAdv.auto_adv`` содержит сам ``AdvSetting``, без вложенного
        атрибута ``adv_setting``.
        """
        fact = await PlanFactController._resolve_fact_for_pre_adv(pre_adv)
        if fact is None:
            logger.warning(
                "plan_fact: пропуск adv_id=%s — нет keywords в Redis и нет plan_fact_summary",
                pre_adv.adv_id,
            )
            return None
        plan: Optional[PlanData] = PlanFactProvider.get_plan_data(
            pre_adv.auto_adv
        )
        return PlanFactStatDTO.create(
            adv_id=pre_adv.adv_id,
            shop_id=pre_adv.auto_adv.wb_cabinet.shop_id,
            plan=plan,
            fact=fact,
            version=version,
        )










