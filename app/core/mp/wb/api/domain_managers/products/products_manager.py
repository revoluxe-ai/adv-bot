"""Доменный менеджер для работы с карточками товаров WB (Content API)."""

from __future__ import annotations

from app.core.mp.wb.api.adapter.content_products_client import ContentProductCardsAdapter
from app.core.mp.wb.api.generated.products.v1.content_products_client.models import (
    PostContentV2GetCardsListBody,
    PostContentV2GetCardsListResponse200,
)


class ProductsManager:
    """
    Доменный менеджер для сущностей «карточки товаров» WB Content API.

    Предоставляет высокоуровневые методы получения списка карточек с пагинацией
    и фильтрами.
    """

    def __init__(self, product_cards_adapter: ContentProductCardsAdapter) -> None:
        self._product_cards_adapter = product_cards_adapter

    async def get_cards_list(
        self,
        body: PostContentV2GetCardsListBody,
        locale: str | None = None,
    ) -> PostContentV2GetCardsListResponse200 | None:
        """
        Получить список карточек товаров поставщика с пагинацией и фильтрами.

        Использует WB Content API (POST /content/v2/get/cards/list). Возвращает
        объект с полем ``cards`` (список карточек) и ``cursor`` (данные для
        следующей страницы). Карточки, находящиеся в корзине, в ответ не входят;
        для них есть отдельный метод API.

        Args:
            body: Настройки запроса: сортировка (sort), фильтры (filter),
                курсор пагинации (cursor с limit, updatedAt, nmID и т.д.).
                Для первой страницы обычно передают cursor.limit (например 100)
                и при необходимости sort (например ascending: true).
            locale: Локаль ответа (например "ru"). Необязательный параметр.

        Returns:
            При успехе — объект с полями ``cards`` (список карточек) и ``cursor``
            (пагинация). При ошибке или неожиданном ответе — None. При 400/401/
            403/429 адаптер пробрасывает исключения (BadRequestError,
            ApiForbiddenError, TooManyRequests и т.д.).

        Note:
            Лимиты Content API: 100 запросов в минуту на аккаунт поставщика,
            интервал между запросами 600 ms, burst до 5 запросов. Часть методов
            (создание карточек, обновление, список с ошибками) имеют отдельные
            лимиты.
        """
        return await self._product_cards_adapter.get_cards_list(
            body=body,
            locale=locale,
        )
