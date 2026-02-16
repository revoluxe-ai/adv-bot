"""Адаптер методов WB Content API (карточки товаров)."""

from __future__ import annotations

from app.core.mp.wb.api.adapter.abc_group_client import AbcAdapter
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.adapter.sections_enum import SectionsEnum
from app.core.mp.wb.api.retry_decorator import retry_decorator
from app.core.mp.wb.api.generated.products.v1.content_products_client.api.kartochki_tovarov import (
    post_content_v2_get_cards_list,
)
from app.core.mp.wb.api.generated.products.v1.content_products_client.models import (
    PostContentV2GetCardsListBody,
    PostContentV2GetCardsListResponse200,
)
from app.core.mp.wb.api.generated.products.v1.content_products_client.types import UNSET


class ContentSectionAdapter(AbcAdapter):
    """Базовый адаптер для секции Content (карточки товаров, теги и т.д.)."""

    section = SectionsEnum.CONTENT


class ContentProductCardsAdapter(ContentSectionAdapter):
    """
    Адаптер для методов раздела «Карточки товаров» WB Content API.

    Обеспечивает получение списка карточек с пагинацией и фильтрами.
    """

    @retry_decorator(period=2, limit=3)
    async def get_cards_list(
        self,
        body: PostContentV2GetCardsListBody,
        locale: str | None = None,
    ) -> PostContentV2GetCardsListResponse200 | None:
        """
        Получить список карточек товаров поставщика с пагинацией и фильтрами.

        Вызывает POST /content/v2/get/cards/list. В ответе — список карточек (cards)
        и курсор для следующей страницы (cursor). Карточки в корзине в ответ не входят.

        Args:
            body: Настройки запроса (sort, filter, cursor с limit и т.д.).
            locale: Локаль ответа (например, "ru"). Опционально.

        Returns:
            Объект с полями cards и cursor при успехе, None при ошибке (если не
            используется raise_on_unexpected_status). При 400/401/403/429
            with_raise_errors пробрасывает исключения.

        Note:
            Лимиты Content API: 100 запросов/мин, интервал 600 ms, burst 5.
        """
        client = await self.auth_client_handler.get_proxy_client(self)
        locale_param = locale if locale is not None else UNSET
        response = await with_raise_errors(
            post_content_v2_get_cards_list.asyncio_detailed,
            client,
            body=body,
            locale=locale_param,
        )
        if response is None or response.parsed is None:
            return None
        parsed = response.parsed
        if isinstance(parsed, PostContentV2GetCardsListResponse200):
            return parsed
        return None
