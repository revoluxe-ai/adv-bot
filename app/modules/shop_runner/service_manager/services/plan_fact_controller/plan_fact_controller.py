import logging
from typing import Optional

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater import (
    AdvSettingAutoUpdater,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.dto.plan_fact_stat_dto import PlanFactStatDTO

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)

logger = logging.getLogger(__name__)


class PlanFactController:
    """Контроллер для обработки план-факта данных одной кампании"""

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
        try:
            # Получаем план данные (синхронно)
            plan: Optional[PlanData] = AdvSettingAutoUpdater.get_plan_data(
                adv.adv_setting
            )

            # Получаем факт данные (асинхронно)
            fact: Optional[FactData] = None
            try:
                keywords = await adv.get_keywords()
                auto_updater = AdvSettingAutoUpdater(adv.adv_setting)
                fact = await auto_updater.get_fact_data(keywords)
            except Exception as exc:
                logger.error(
                    "Ошибка получения факта для adv_id=%s: %s",
                    adv.adv_id,
                    exc,
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

        except Exception as exc:
            logger.error(
                "Ошибка обработки план-факта для adv_id=%s: %s",
                adv.adv_id,
                exc,
                exc_info=True,
            )
            return None




