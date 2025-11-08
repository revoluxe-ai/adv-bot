"""Утилита для поиска позиций товара по ключу в выдаче Wildberries.

Пример использования:

    poetry run python scripts/find_keyword_positions.py \
        --keyword "картина" \
        --nmid 12345678

Скрипт перебирает страницы выдачи (до 60 страниц по правилам WB) и
выводит, на каких страницах и на каких позициях найден указанный
артикул (nmid). Никакие данные в Redis не сохраняются.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import dataclass
from collections.abc import Iterable

from aiogram.client.session import aiohttp

from app.modules.wb_keywords_parser.wb_parser.playwright_fetch import (
    fetch_wb_search,
    resolve_profile_dir,
)
from app.settings import settings

logger = logging.getLogger(__name__)

MAX_WB_PAGES = 60


def build_parse_url(keyword: str, page: int) -> str:
    """Сформировать URL запроса к поиску WB."""

    assert 1 <= page <= MAX_WB_PAGES
    return (
        "https://search.wb.ru/exactmatch/ru/common/v5/search"
        "?ab_testing=false"
        "&appType=32"
        "&curr=rub"
        "&dest=-1257786"
        f"&page={page}"
        f"&query={keyword}"
        "&resultset=catalog"
        "&sort=popular"
        "&suppressSpellcheck=false"
    )


@dataclass
class ProductPlacement:
    """Информация о найденном товаре."""

    nmid: int
    page: int
    index_on_page: int
    absolute_position: int
    name: str | None


async def fetch_page(
    session: aiohttp.ClientSession, keyword: str, page: int
) -> tuple[list[dict], int | None]:
    """Получить сырые данные по ключу и странице."""

    url = build_parse_url(keyword, page)
    logger.debug("Запрос к %s", url)

    async with session.get(url) as response:
        response.raise_for_status()
        response_text = await response.text()

    if not response_text:
        return [], None

    data = json.loads(response_text)

    try:
        payload_version = data["payloadVersion"]
    except KeyError as exc:
        raise ValueError("Ответ WB не содержит версии payload") from exc

    if payload_version != 2:
        raise ValueError(f"Неизвестная версия payload: {payload_version}")

    products = data.get("data", {}).get("products", [])
    total_items = data.get("data", {}).get("total")
    return products, total_items


async def iter_positions(
    keyword: str, nmids: Iterable[int], max_pages: int
) -> list[ProductPlacement]:
    """Обойти выдачу WB и собрать позиции указанных nmid."""

    targets = set(nmids)
    found: list[ProductPlacement] = []
    last_page = max_pages

    page = 1

    async with aiohttp.ClientSession() as session:
        while page <= last_page:
            products, total_items = await fetch_page(session, keyword, page)

            if total_items is not None:
                calculated_pages = (total_items + 99) // 100
                if calculated_pages == 0:
                    last_page = min(last_page, 1)
                else:
                    last_page = min(max_pages, calculated_pages)

            if not products:
                page += 1
                continue

            for index, product in enumerate(products):
                try:
                    nmid = int(product["id"])
                except (KeyError, TypeError, ValueError):
                    continue

                if nmid not in targets:
                    continue

                absolute_position = (page - 1) * 100 + index + 1
                name = product.get("name")
                found.append(
                    ProductPlacement(
                        nmid=nmid,
                        page=page,
                        index_on_page=index + 1,
                        absolute_position=absolute_position,
                        name=name,
                    )
                )

            page += 1

    return found


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Найти позиции товара (nmid) по ключу в поисковой выдаче Wildberries."
        )
    )
    parser.add_argument("--keyword", required=True, help="Ключевое слово для поиска")
    parser.add_argument(
        "--nmid",
        dest="nmids",
        type=int,
        nargs="+",
        required=True,
        help="Список артикулов (nmid), позиции которых нужно найти",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=MAX_WB_PAGES,
        help="Максимальное количество страниц для проверки (по умолчанию 60)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Включить подробный лог",
    )
    parser.add_argument(
        "--backend",
        choices=("http", "playwright"),
        default="playwright",
        help="Бэкенд поиска: HTTP клиент или Playwright (по умолчанию Playwright)",
    )
    return parser.parse_args()


async def main_async(
    keyword: str, nmids: Iterable[int], max_pages: int, backend: str
) -> None:
    if backend == "http":
        placements = await iter_positions(keyword, nmids, max_pages)

        if not placements:
            unique_nmids = sorted(set(nmids))
            print(
                "Товары {} не найдены в выдаче по заданному ключу".format(
                    ", ".join(str(nmid) for nmid in unique_nmids)
                )
            )
            return

        for placement in sorted(placements, key=lambda p: (p.page, p.index_on_page)):
            product_title = f" ({placement.name})" if placement.name else ""
            print(
                f"Товар {placement.nmid}{product_title} найден на странице {placement.page}, позиция на странице {placement.index_on_page}, общая позиция {placement.absolute_position}"
            )

        found_nmid = {placement.nmid for placement in placements}
        missing = set(nmids) - found_nmid
        if missing:
            print(
                "Не найдены в выдаче: {}".format(
                    ", ".join(str(nmid) for nmid in sorted(missing))
                )
            )
        return

    profile_dir = resolve_profile_dir(settings.WB_PLAYWRIGHT_PROFILE_ROOT, keyword)
    products, cluster, preset, total_items = await fetch_wb_search(
        keyword,
        1,
        timeout_sec=settings.WB_PLAYWRIGHT_TIMEOUT_SEC,
        headless=settings.WB_PLAYWRIGHT_HEADLESS,
        profile_dir=profile_dir,
        proxy_url=settings.WB_PLAYWRIGHT_PROXY_URL,
    )

    print(
        "Playwright backend: %s товаров, cluster=%s, preset=%s, total_items=%s"
        % (len(products), cluster, preset, total_items)
    )

    target_nmids = set(nmids)

    if not target_nmids:
        return

    found_positions: list[ProductPlacement] = []
    for index, product in enumerate(products):
        try:
            nmid = int(product["id"])
        except (KeyError, TypeError, ValueError):
            continue
        if nmid not in target_nmids:
            continue
        absolute_position = index + 1
        found_positions.append(
            ProductPlacement(
                nmid=nmid,
                page=1,
                index_on_page=index + 1,
                absolute_position=absolute_position,
                name=product.get("name"),
            )
        )

    if not found_positions:
        print(
            "Товары {} не найдены на первой странице".format(
                ", ".join(str(nmid) for nmid in sorted(target_nmids))
            )
        )
        return

    for placement in found_positions:
        product_title = f" ({placement.name})" if placement.name else ""
        print(
            f"Товар {placement.nmid}{product_title} найден на странице {placement.page}, позиция на странице {placement.index_on_page}, общая позиция {placement.absolute_position}"
        )


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        normalized_keyword = args.keyword.strip()
        max_pages = max(1, min(args.max_pages, MAX_WB_PAGES))
        if args.max_pages != max_pages:
            logger.warning(
                "Количество страниц ограничено диапазоном от 1 до %s. Будет использовано значение %s",
                MAX_WB_PAGES,
                max_pages,
            )
        asyncio.run(
            main_async(normalized_keyword, args.nmids, max_pages, args.backend)
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
