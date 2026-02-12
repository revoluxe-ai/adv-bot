"""Адаптер методов WB Promotion API: предметы поставщика и номенклатура для рекламы."""

from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.api.parametry_kampanij import (
    get_adv_v1_auto_getnmtoadd,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.api.sozdanie_kampanij import (
    get_adv_v1_supplier_subjects,
    post_adv_v2_supplier_nms,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    GetAdvV1SupplierSubjectsResponse200Type0Item,
    PostAdvV2SupplierNmsResponse200Item,
)
from app.core.mp.wb.api.retry_decorator import retry_decorator


class ProductCardsAdapter(BaseSectionAdapter):
    """
    Адаптер методов WB Promotion API для получения списков предметов и номенклатуры,
    доступных для добавления в рекламные кампании.
    """

    @retry_decorator(period=2, limit=3)
    async def get_supplier_subjects(
        self,
        payment_type: str = "cpm",
    ) -> list[GetAdvV1SupplierSubjectsResponse200Type0Item] | None:
        """
        Получить список предметов (категорий) поставщика, по которым есть карточки,
        доступные для рекламы.

        Вызывает GET /adv/v1/supplier/subjects. Каждый элемент содержит id, name, count.

        Args:
            payment_type: Тип оплаты (например "cpm"). По умолчанию "cpm".

        Returns:
            Список предметов при успехе, None при ошибке или пустом ответе.
        """
        client = await self.auth_client_handler.get_proxy_client(self)
        response = await with_raise_errors(
            get_adv_v1_supplier_subjects.asyncio_detailed,
            client,
            payment_type=payment_type,
        )
        if response is None or response.parsed is None:
            return None
        parsed = response.parsed
        if isinstance(parsed, list):
            return parsed # type: ignore[return-value] # https://github.com/microsoft/pyright/issues/3273
        return None

    @retry_decorator(period=2, limit=3)
    async def post_supplier_nms(
        self,
        body: list[int],
    ) -> list[PostAdvV2SupplierNmsResponse200Item] | None:
        """
        По списку nm_id получить карточки поставщика, доступные для добавления в рекламу.

        Вызывает POST /adv/v2/supplier/nms. Лимит: 5 запросов в минуту, интервал 12 с.

        Args:
            body: Список номенклатурных идентификаторов (nm_id).

        Returns:
            Список карточек (title, nm, subject_id) при успехе. При 400 возвращается
            текст ошибки (with_raise_errors пробрасывает BadRequestError). None при
            ином неуспешном ответе.
        """
        client = await self.auth_client_handler.get_proxy_client(self)
        response = await with_raise_errors(
            post_adv_v2_supplier_nms.asyncio_detailed,
            client,
            body=body,
        )
        if response is None or response.parsed is None:
            return None
        parsed = response.parsed
        if isinstance(parsed, list):
            return parsed # type: ignore[return-value] # https://github.com/microsoft/pyright/issues/3273
        return None

    @retry_decorator(period=2, limit=3)
    async def get_auto_nms_to_add(self, adv_id: int) -> list[int] | None:
        """
        Получить список nm_id, доступных для добавления в авторекламу по кампании.

        Вызывает GET /adv/v1/auto/getnmtoadd?id=... В документации WB метод помечен
        как устаревающий (удаление запланировано).

        Args:
            adv_id: Идентификатор рекламной кампании (автореклама).

        Returns:
            Список номенклатурных идентификаторов при успехе, None при ошибке.
        """
        client = await self.auth_client_handler.get_proxy_client(self)
        response = await with_raise_errors(
            get_adv_v1_auto_getnmtoadd.asyncio_detailed,
            client,
            id=adv_id,
        )
        if response is None or response.parsed is None:
            return None
        parsed = response.parsed
        if isinstance(parsed, list):
            return parsed # type: ignore[return-value] # https://github.com/microsoft/pyright/issues/3273
        return None
