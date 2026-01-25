import logging
from collections.abc import Sequence
from typing import cast
from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.plan_fact import PlanFactProvider
from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.shop_runner.service_manager.wb_shop_data_manager.single_run_decorator import (
    single_run,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import (
    TasksManager,
    run_tasks,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


class WBShopDataManager:
    def __init__(
        self,
        wb_cabinet: WBCabinet,
        tasks_manager: TasksManager | None = None,
    ):
        self._wb_cabinet: WBCabinet = wb_cabinet
        self.shop_id: str = wb_cabinet.shop_id
        self._tasks_manager: TasksManager | None = tasks_manager

    @single_run()
    async def __get_calculated_keywords(self, complex_adv: ComplexAdv) -> list[CalculatedKeyword]:
        from app.modules.wb_adv_updater.phrases_processor import get_good_bad_phrases

        if not complex_adv:
            raise RuntimeError("Сначала обновить модели")
        try:
            keywords = await get_good_bad_phrases(complex_adv)
        except Exception as exc:
            raise exc

        return keywords

    @single_run()
    async def _get_active_advs(self) -> list[AdvSetting]:
        shop_id = self.shop_id
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .filter(WBCabinet.shop_id == shop_id, AdvSetting.active_status != 'done')
        )
        async with sm() as session:
            result = await session.execute(stmt)
            advs: Sequence[AdvSetting] = result.scalars().all()
        adv_settings_list = list(advs)
        if not adv_settings_list:
            raise NotFoundActiveAdvCompany("Нет активных кампаний")
        return adv_settings_list

    @staticmethod
    async def __get_adv_id_to_search_adv_map(
        search_id_ids: set[int],
    ) -> dict[int, AdvSetting]:
        stmt = select(AdvSetting).where(AdvSetting.adv_id.in_(search_id_ids))
        async with sm() as session:
            result = await session.execute(stmt)
            advs: Sequence[AdvSetting] = result.scalars().all()
        adv_dict: dict[int, AdvSetting] = {adv.adv_id: adv for adv in advs}
        return adv_dict

    @single_run()
    async def get_wb_adv_dto(self) -> list[WBAdvDTO]:
        complex_advs = await self.get_complex_advs()
        if not complex_advs:
            return []

        handlers = [
            lambda complex_adv=adv: self.__build_wb_adv_dto(complex_adv)
            for adv in complex_advs
        ]

        max_workers = max(1, min(len(handlers), 16))
        results = await run_tasks(
            handlers,
            max_workers=max_workers,
            tasks_manager=self._tasks_manager,
            return_exceptions=True,
        )

        successful_dtos: list[WBAdvDTO] = []
        for adv, result in zip(complex_advs, results):
            if isinstance(result, BaseException):
                logger.error(
                    "Ошибка сбора план-факта для adv_id=%s shop_id=%s: %s",
                    adv.adv_id,
                    adv.shop_id,
                    result,
                )
                continue
            successful_dtos.append(result)

        return successful_dtos

    async def __build_wb_adv_dto(self, complex_adv: ComplexAdv) -> WBAdvDTO:
        plan = PlanFactProvider.get_plan_data(complex_adv.adv_setting)
        if plan is None:
            raise RuntimeError(
                "Plan data is not configured for adv_id=%s" % complex_adv.adv_id
            )
        keywords = await complex_adv.get_keywords()
        provider = PlanFactProvider(complex_adv.adv_setting)
        fact = await provider.get_fact_data(keywords)
        return WBAdvDTO(
            complex_adv=complex_adv,
            plan=plan,
            fact=fact,
        )

    @single_run()
    async def get_complex_advs(self) -> list["ComplexAdv"]:
        adv_settings: list[AdvSetting] = cast(
            list[AdvSetting], await self._get_active_advs()
        )
        search_adv_ids: set[int] = {
            adv.search_adv_id for adv in adv_settings if adv.search_adv_id
        }
        search_adv_idv: dict[int, AdvSetting] = (
            await self.__get_adv_id_to_search_adv_map(search_adv_ids)
        )
        complex_advs: list[ComplexAdv] = []
        for adv in adv_settings:
            search_adv = (
                search_adv_idv.get(adv.search_adv_id)
                if adv.search_adv_id is not None
                else None
            )
            complex_adv = ComplexAdv(
                shop_id=self.shop_id,
                adv_setting=adv,
                get_keywords_func=self.__get_calculated_keywords,
                search_adv=search_adv,
            )
            complex_advs.append(complex_adv)
        # TODO: Нашел лютый баг: все падало, если хотя бы в 1 РК нет nmids
        complex_advs = [adv for adv in complex_advs if adv.nmids]
        return complex_advs





# TODO: Реализовать гибкую модель управления через плавающую мощность и расчет потенциала от текущего статуса
