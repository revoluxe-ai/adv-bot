"""Доменный менеджер для работы с карточками товаров WB (Content API)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from app.core.wb_api.data_classes.card_from_wb import CardFromWB
from app.core.wb_api.mixins.excs import CardNotFoundInWB
from app.core.mp.wb.api.adapter.content_products_client import ContentProductCardsAdapter
from app.core.mp.wb.api.generated.products.v1.content_products_client.models import (
    PostContentV2GetCardsListBody,
    PostContentV2GetCardsListBodySettings,
    PostContentV2GetCardsListBodySettingsCursor,
    PostContentV2GetCardsListBodySettingsFilter,
    PostContentV2GetCardsListBodySettingsSort,
    PostContentV2GetCardsListResponse200,
)
from app.core.mp.wb.api.generated.products.v1.content_products_client.types import UNSET


@dataclass(frozen=True)
class ProductCardInfo:
    """DTO карточки товара с полями, совместимыми с вызовами (name, nmid)."""

    name: str
    nmid: int


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

    async def get_card_by_nmid(self, nmid: int) -> ProductCardInfo | None:
        """
        Получить карточку товара по артикулу WB (nmID).

        Использует Content API с фильтром textSearch. При отсутствии карточки
        выбрасывает CardNotFoundInWB.
        """
        filter_ = PostContentV2GetCardsListBodySettingsFilter(
            text_search=str(nmid),
            with_photo=-1,
        )
        cursor = PostContentV2GetCardsListBodySettingsCursor(limit=1)
        sort = PostContentV2GetCardsListBodySettingsSort(ascending=False)
        settings = PostContentV2GetCardsListBodySettings(
            filter_=filter_,
            cursor=cursor,
            sort=sort,
        )
        body = PostContentV2GetCardsListBody(settings=settings)
        response = await self.get_cards_list(body=body)
        if response is None:
            raise CardNotFoundInWB(
                f"Карточка с артикулом {nmid} не найдена на Wildberries"
            )
        cards = response.cards
        if cards is UNSET or not cards:
            raise CardNotFoundInWB(
                f"Карточка с артикулом {nmid} не найдена на Wildberries"
            )
        card = cards[0]
        raw_nm_id = card.nm_id
        nm_id = nmid if raw_nm_id is UNSET else int(cast(int, raw_nm_id))
        title = str(card.title) if card.title is not UNSET else str(nmid)
        return ProductCardInfo(name=str(title), nmid=nm_id)

    async def get_card_by_nmid_for_db(
        self, nmid: int
    ) -> tuple["ProductCardInfo", "CardFromWB"] | None:
        """
        Получить карточку по nmid и CardFromWB для update_cards_in_db.
        Возвращает (ProductCardInfo, CardFromWB).
        """
        from app.core.wb_api.data_classes.card_from_wb import CardFromWB

        filter_ = PostContentV2GetCardsListBodySettingsFilter(
            text_search=str(nmid),
            with_photo=-1,
        )
        cursor = PostContentV2GetCardsListBodySettingsCursor(limit=1)
        sort = PostContentV2GetCardsListBodySettingsSort(ascending=False)
        settings = PostContentV2GetCardsListBodySettings(
            filter_=filter_,
            cursor=cursor,
            sort=sort,
        )
        body = PostContentV2GetCardsListBody(settings=settings)
        response: PostContentV2GetCardsListResponse200 | None = await self.get_cards_list(body=body)
        if response is None:
            raise CardNotFoundInWB(
                f"Карточка с артикулом {nmid} не найдена на Wildberries"
            )
        cards = response.cards
        if cards is UNSET or not cards:
            raise CardNotFoundInWB(
                f"Карточка с артикулом {nmid} не найдена на Wildberries"
            )
        card = cards[0]
        raw_nm_id = card.nm_id
        if raw_nm_id is UNSET:
            return None
        resolved_nmid = cast(int, raw_nm_id)
        title_val = str(card.title) if card.title is not UNSET else str(resolved_nmid)
        info = ProductCardInfo(name=str(title_val), nmid=resolved_nmid)
        card_from_wb = CardFromWB(card.to_dict())
        return info, card_from_wb
