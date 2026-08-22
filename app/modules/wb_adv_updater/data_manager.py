"""Сервисные операции обновления данных кампаний/карточек и вспомогательных расчётов."""

import asyncio
import cProfile
import json
import logging
import pstats
import time
from dataclasses import dataclass
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from typing import Any, cast

from dependency_injector.wiring import Provide, inject
from PIL import Image  # type: ignore
from sqlalchemy import and_, func, select

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, load_only
from sqlalchemy.sql.functions import coalesce

from app.client_bot.const import ALWAYS_ON
from app.core.redis_manager_v2.redis_client import RedisClient
from app.exc import (
    CardNotFoundInDB,
)

from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)
from app.modules.common_slaves.wildberries.exceptions import NotItemsInAdvSetting
from app.modules.common_slaves.wildberries.data_classes.card_from_wb import CardFromWB
from app.modules.common_slaves.wildberries.models import (
    AdvKeyword,
    AdvSetting,
    KeywordSetting,
    WBCard,
    WBCategory,
    WBUserCabinet,
)
from app.modules.shop_runner.service_manager.services.v3_status_mode_sync import (
    sync_keyword_setting_mode_for_v3,
)
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from app.modules.relevant_phrase_manager import RelevantPhraseManager
from app.utils import redis_manager
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.assoc_tables import favorite_advs_association
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from app.utils.redis_manager.exc import DataNotFoundError
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from ..common_slaves.wildberries.models.wb_cabinet import WBCabinet
from ..common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from ..common_slaves.wildberries import wb_db_manager


logger = logging.getLogger(__name__)

_sm = get_async_session_maker
_ensure_card_locks: dict[tuple[str, int], asyncio.Lock] = {}
_ensure_card_locks_guard = asyncio.Lock()


@dataclass(slots=True)
class CardImageEnsureResult:
    ok: bool
    reason: str | None = None


async def _card_exists_in_db(nmid: int) -> bool:
    async with _sm(read_only=True) as session:
        stmt = select(WBCard.nmid).where(WBCard.nmid == nmid).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None


async def _get_wb_cabinet_by_shop_id(shop_id: str) -> WBCabinet | None:
    async with _sm(read_only=True) as session:
        stmt = select(WBCabinet).where(WBCabinet.shop_id == shop_id).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def _get_ensure_lock(key: tuple[str, int]) -> asyncio.Lock:
    async with _ensure_card_locks_guard:
        lock = _ensure_card_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _ensure_card_locks[key] = lock
        return lock


async def _cleanup_ensure_lock(key: tuple[str, int], lock: asyncio.Lock) -> None:
    async with _ensure_card_locks_guard:
        current_lock = _ensure_card_locks.get(key)
        if current_lock is lock and not lock.locked():
            _ = _ensure_card_locks.pop(key, None)


async def _card_has_photo_in_db(nmid: int) -> bool:
    async with _sm(read_only=True) as session:
        stmt = select(WBCard).where(WBCard.nmid == nmid).limit(1)
        result = await session.execute(stmt)
        wb_card = result.scalar_one_or_none()
        if wb_card is None:
            return False
        try:
            photos = wb_card.photos
        except Exception:
            return False
        return bool(photos)


async def ensure_card_in_db(shop_id: str, nmid: int, *, timeout_sec: int = 60) -> bool:
    """Убедиться, что карточка артикула есть в БД.

    Возвращает True, если карточка найдена/успешно загружена.
    Возвращает False, если за timeout_sec не удалось подтвердить наличие карточки в БД.
    Может пробросить CardNotFoundInWB и ошибки доступа к WB API.
    """
    if nmid <= 0:
        return False
    if await _card_exists_in_db(nmid):
        return True

    key = (shop_id, nmid)
    lock = await _get_ensure_lock(key)
    try:
        async with lock:
            if await _card_exists_in_db(nmid):
                return True

            wb_cabinet = await _get_wb_cabinet_by_shop_id(shop_id)
            if wb_cabinet is None:
                logger.warning(
                    "ensure_card_in_db: wb_cabinet not found for shop_id=%s, nmid=%s",
                    shop_id,
                    nmid,
                )
                return False

            from app.core.di.app_container import AppContainer
            from app.core.di.di_manager import DIManager

            async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
                container_any: Any = cast(Any, container)
                factory: Any = cast(
                    Any,
                    container_any.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory(),  # type: ignore[reportUnknownMemberType]
                )
                hub: Any = cast(Any, factory.get_wb_manager_hub(shop_id))  # type: ignore[reportUnknownMemberType]
                card_result: tuple[Any, CardFromWB] = cast(
                    tuple[Any, CardFromWB],
                    await cast(
                        Any,
                        hub.wb_data_manager.products_manager.get_card_by_nmid_for_db,  # type: ignore[reportUnknownMemberType]
                    )(nmid),
                )
                _, target_card = card_result
            await wb_db_manager.update_cards_in_db([target_card], wb_cabinet)

            deadline = time.monotonic() + timeout_sec
            while time.monotonic() < deadline:
                if await _card_exists_in_db(nmid):
                    return True
                await asyncio.sleep(0.5)
            return False
    finally:
        await _cleanup_ensure_lock(key, lock)


async def ensure_card_with_image_for_ui(
    shop_id: str,
    nmid: int,
    *,
    timeout_sec: int = 60,
) -> CardImageEnsureResult:
    """Проверить, что карточка и фото готовы для UI меню РК."""
    if nmid <= 0:
        return CardImageEnsureResult(ok=False, reason="invalid_nmid")

    if await _card_exists_in_db(nmid) and await _card_has_photo_in_db(nmid):
        return CardImageEnsureResult(ok=True)

    try:
        card_ready = await ensure_card_in_db(shop_id, nmid, timeout_sec=timeout_sec)
    except Exception as exc:
        logger.warning(
            "ensure_card_with_image_for_ui failed for shop_id=%s nmid=%s: %s",
            shop_id,
            nmid,
            exc,
        )
        return CardImageEnsureResult(ok=False, reason="ensure_card_failed")

    if not card_ready:
        return CardImageEnsureResult(ok=False, reason="card_not_loaded")
    if not await _card_has_photo_in_db(nmid):
        return CardImageEnsureResult(ok=False, reason="photo_missing")
    return CardImageEnsureResult(ok=True)


async def get_keyword_statistic_clickhouse(
    client: Any,
    text: str,
    adv_ids: set[int],
    pass_days: int | None = 7,
) -> tuple[int, int, float]:
    """
    Возвращает суммарную статистику по ключевому слову text из агрегатов
    ``default_db.mv_clusters_daily_agg``:
    - total_clicks
    - total_views
    - total_spend

    Имя БД MUST быть в тексте SQL (рабочий контур ``default_db``); session
    ``client.database`` не заменяет квалификацию. Spec:
    ``clickhouse-query-database-qualification``.
    """

    if not adv_ids:
        return 0, 0, 0.0

    today = datetime.now().date()
    date_filter = ""
    if pass_days:
        start_date = today - timedelta(days=pass_days)
        date_filter = f"AND date >= '{start_date}'"

    adv_ids_str = ", ".join(map(str, adv_ids))

    # Qualified MV: working-contour addressing requires ``default_db.`` in SQL
    # text (spec: clickhouse-query-database-qualification).
    query = f"""
        WITH keyword_stats AS (
            SELECT
                argMaxMerge(views_state) AS views,
                argMaxMerge(clicks_state) AS clicks,
                argMaxMerge(cpm_state) AS cpm
            FROM default_db.mv_clusters_daily_agg
            WHERE
                adv_id IN ({adv_ids_str})
                AND norm_query = %(text)s
                {date_filter}
            GROUP BY adv_id, nmid, norm_query, date
        )
        SELECT
            COALESCE(SUM(clicks), 0) AS total_clicks,
            COALESCE(SUM(views), 0) AS total_views,
            COALESCE(SUM(cpm * views) / 1000.0, 0.0) AS total_spend
        FROM keyword_stats
    """
    async with anti_ch_crash_semaphore:
        result = await client.query(query, parameters={"text": text})

    if not result.result_rows:
        return 0, 0, 0.0

    total_clicks, total_views, total_spend = result.result_rows[0]

    if total_clicks > total_views:
        total_views = total_clicks

    return int(total_clicks), int(total_views), float(total_spend)


async def get_global_super_wb_user_cabinet() -> WBUserCabinet:
    async with _sm() as session:
        stmt = select(User).options(selectinload(User.wb_tokens))
        result = await session.execute(stmt)
        users: Sequence[User] = list(result.unique().scalars().all())
        all_tokens = [wb_token for user in users for wb_token in user.wb_tokens]
        super_user = User()
        super_user.wb_tokens = all_tokens
        wb_user_cabinet = WBUserCabinet()
        wbcabinet = WBCabinet()
        wb_user_cabinet.wb_cabinet = wbcabinet
        wb_user_cabinet.user = super_user
    return wb_user_cabinet


# def __sort_by_update_keyword(keyword: WBItemPosition) -> datetime:
#     if not (update := keyword.timestamp):
#         update = datetime.now() - timedelta(days=1000)
#     return update


# async def set_positions(
#     keyword_stats: list[CalculatedKeyword], adv_setting: AdvSetting
# ) -> list[CalculatedKeyword]:
#     # TODO: Вынести локальный импорт, и вообще разобраться со всеми локальными импортами в проекте
#     from ..shop_runner.service_manager.services.keyword_stamp_manager import (
#         ClickHouseKeywordStampManager,
#     )
#
#     positions: list[WBItemPosition] = (
#         await ClickHouseKeywordStampManager.get_last_positions(adv_setting)
#     )
#     if not positions:
#         return keyword_stats
#     text_to_position = {position.keyword_text: position for position in positions}
#     for keyword_stat in keyword_stats:
#         position = text_to_position.get(keyword_stat.text)
#         if position:
#             keyword_stat.position = position
#
#     return keyword_stats


# async def set_position(
#     keyword_stat: CalculatedKeyword, adv_setting: AdvSetting
# ) -> CalculatedKeyword:
#     text = keyword_stat.text
#     main_nmid = int(adv_setting.nmids[0])
#     position = await redis_manager.get_keyword_position(text, main_nmid)
#     if position:
#         keyword_stat.position = position.position
#
#     else:
#         keywords = keyword_stat.childs_keywords
#         if keywords:
#             texts = [kw.text for kw in keywords]
#             # Type ignore for untyped redis_manager call
#             positions = await redis_manager.get_keywords_positions(adv_setting, texts)  # type: ignore[no-untyped-call]
#             if positions:
#                 position = max(positions, key=lambda kw: __sort_by_update_keyword(kw))
#                 assert position
#                 keyword_stat.position = position.position
#
#     return keyword_stat

#
# async def get_keywords_positions(
#     adv_setting: AdvSetting, texts: list[str]
# ) -> list[WBItemPosition]:
#     """Get keywords positions from Redis."""
#     # Type ignore for untyped redis_manager call and return type
#     return await redis_manager.get_keywords_positions(adv_setting, texts)  # type: ignore[no-untyped-call,no-any-return]

#
# def __calculate_clusters(
#     preset_to_keywords: dict[Any, list[CalculatedKeyword]],
#     preset_to_cluster_name: dict[Any, str],
# ) -> list[CalculatedKeyword]:
#     keyword_stats = []
#     for preset in preset_to_keywords:
#         keywords = preset_to_keywords[preset]
#         keyword_cluster_name = preset_to_cluster_name[preset]
#         views = 0
#         clicks = 0
#         spend = 0
#         query: int = 0
#         for keyword in keywords:
#             views += keyword.views
#             clicks += keyword.clicks
#             spend += int(keyword.spend)
#             if isinstance(keyword.query, int):
#                 query += keyword.query
#             elif isinstance(keyword.query, str) and keyword.query.isdigit():
#                 query += int(keyword.query)
#
#         cluster_keyword = CalculatedKeyword(
#             text=keyword_cluster_name, views=views, clicks=clicks, spend=spend
#         )
#         cluster_keyword.query = str(query) if query else "<50"
#         cluster_keyword.childs_keywords = keywords
#         keyword_stats.append(cluster_keyword)
#
#     return keyword_stats


def profile_function(inner_func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    profiler = cProfile.Profile()
    profiler.enable()
    inner_func(*args, **kwargs)
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumulative")
    _ = stats.print_stats(10)


# async def convert_keyword_stats_in_clusters(
#     keyword_stats: list[CalculatedKeyword],
# ) -> list[CalculatedKeyword]:
#     preset_to_keywords = defaultdict(list)
#     preset_to_cluster_name = {}
#     texts = [keyword.text for keyword in keyword_stats]
#     try:
#         text_to_custer_and_present: dict[str, tuple[str, int]] = (
#             await redis_manager.get_clusters_and_presets(texts)
#         )
#     except Exception as e:
#         logger.error(
#             f"Ошибк {e} получения кластеров и пресетов: {texts}", exc_info=True
#         )
#         return keyword_stats
#     for keyword in keyword_stats:
#         text = keyword.text
#         cluster_name, preset = text_to_custer_and_present.get(text, (None, None))
#         if cluster_name:
#             preset_to_keywords[preset].append(keyword)
#             preset_to_cluster_name[preset] = cluster_name
#         else:
#             preset = hash(text)
#             cluster_name = text
#             preset_to_keywords[preset].append(keyword)
#             preset_to_cluster_name[preset] = cluster_name
#     keyword_stats = __calculate_clusters(preset_to_keywords, preset_to_cluster_name)
#
#     return keyword_stats


# Функции get_cpm_by_nmid и __get_cpm_from_positions удалены,
# так как CPM больше не доступен из позиций парсинга


async def get_full_adv_stat_for_adv_id_from_redis(adv_id: int) -> FullAdvStat | None:
    """Получение Полной статистики из Redis по adv_id"""
    try:
        full_stat_json = await redis_manager.get_full_stat_adv(adv_id)
        full_stat = json.loads(full_stat_json)
        full_stat = FullAdvStat.model_validate(full_stat)
        return full_stat
    except DataNotFoundError:
        return None


async def get_cached_keyword(adv: AdvSetting, text: str) -> CalculatedKeyword | None:
    """Получить закешированное ключевое слово"""
    cache_key = f"good_bad_phrases:{adv.id}:{adv.updated_at.timestamp()}:{text}"  # type: ignore
    cached_data = await redis_manager.get(cache_key)

    if cached_data and isinstance(cached_data, str):
        return CalculatedKeyword.model_validate_json(cached_data)
    return None


async def get_wb_category(adv_setting: AdvSetting) -> WBCategory | None:
    try:
        nmid = adv_setting.nmids[0]
    except Exception as e:
        raise NotItemsInAdvSetting("У кампании в базе нет товаров") from e
    async with _sm() as session:
        smtp = (
            select(WBCard)
            .where(WBCard.nmid == int(nmid))
            .options(selectinload(WBCard.wb_category))
        )
        result = await session.execute(smtp)
    wb_card: WBCard | None = result.scalar_one_or_none()
    if wb_card is not None:
        wb_category = wb_card.wb_category
    else:
        raise CardNotFoundInDB("В базе не найдена карточка товара: " + str(nmid))
    return wb_category


async def get_main_photos(nmids: list[int]) -> list[str]:
    async with _sm() as session:
        smtp = select(WBCard).where(WBCard.nmid.in_(nmids))
        result = await session.execute(smtp)
        wb_cards: list[WBCard] = list(result.unique().scalars().all())
    main_photos: list[str] = [wb_card.photos[0] for wb_card in wb_cards]
    return main_photos


# async def __download_and_resize_image(
#     url: str, session: Any, max_size: int = 1280
# ) -> bytes | None:
#     while True:
#         async with session.get(url) as response:
#             if response.status != 200:
#                 continue
#             image_data = await response.read()
#             # Открываем изображение используя BytesIO
#             with io.BytesIO(image_data) as image_file:
#                 with Image.open(image_file) as img:
#                     # Масштабируем изображение, сохраняя пропорции
#                     img.thumbnail((max_size, max_size))
#
#                     # Сохраняем изображение в BytesIO объект
#                     with io.BytesIO() as output:
#                         img.save(output, format="JPEG")
#                         return output.getvalue()


async def get_adv_keyword_text_in_black_list() -> list[tuple[int, str]]:
    async with _sm() as session:
        stmt = (
            select(KeywordSetting)
            .options(selectinload(KeywordSetting.adv_setting))
            .where(KeywordSetting.hard_status == 0)
        )
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = list(result.unique().scalars().all())
    adv_keyword_text_in_black_list: list[tuple[int, str]] = []
    for keyword_setting in keyword_settings:
        adv_setting = keyword_setting.adv_setting
        adv_keyword_text_in_black_list.append(
            (adv_setting.adv_id, keyword_setting.text)
        )

    return adv_keyword_text_in_black_list


async def get_all_shops_for_user(user: User) -> list[WBUserCabinet]:
    async with _sm() as session:
        stmt = select(WBUserCabinet).where(WBUserCabinet.user_id == user.id)
        result = await session.execute(stmt)
        wb_user_cabinets = result.scalar()
        if wb_user_cabinets:
            return list(wb_user_cabinets.all())
        else:
            return []


# async def get_adv_id_to_min_ctr(adv_ids: list[int]) -> dict[int, float]:
#     async with _sm() as session:
#         stmt = select(AdvSetting).where(AdvSetting.adv_id.in_(adv_ids))
#         result = await session.execute(stmt)
#         adv_settings: list[AdvSetting] = list(result.unique().scalars())
#     adv_id_to_min_ctr = {}
#
#     for adv_setting in adv_settings:
#         logger.debug("Получаю min_ctr")
#         try:
#             min_ctr = await get_min_ctr(adv_setting)
#             logger.debug("min_ctr получен")
#             adv_id_to_min_ctr[adv_setting.adv_id] = min_ctr
#         except Exception as e:
#             logger.error(f"Ошибка при получении min_ctr {e}", exc_info=True)
#             adv_id_to_min_ctr[adv_setting.adv_id] = 0.03
#     return adv_id_to_min_ctr


async def get_adv_id_keyword_text_to_status(
    adv_ids: list[int],
) -> dict[tuple[int, str], int]:
    async with _sm() as session:
        # Используем только необходимые колонки и убираем лишние алиасы
        stmt = (
            select(AdvSetting.adv_id, KeywordSetting.text, KeywordSetting.hard_status)
            .join(KeywordSetting, AdvSetting.id == KeywordSetting.adv_setting_id)
            .where(AdvSetting.adv_id.in_(adv_ids))
        )

        # Выполняем запрос
        result = await session.execute(stmt)

        # Извлекаем данные в виде словаря сразу в процессе итерации по результату
        adv_id_keyword_text_to_status = {
            (row.adv_id, row.text): row.hard_status for row in result
        }

    return adv_id_keyword_text_to_status


# async def get_min_ctr(adv: AdvSetting) -> float:
#     from app.modules.wb_adv_updater.min_ctr_manager.min_ctr_manager import MinCtrManager
#     ctr_manager = MinCtrManager(adv)
#     min_ctr = await ctr_manager.get_min_ctr()
#     return min_ctr


# TODO: Улучшить автоуправление РК
# TODO: Сделать более точным прогноз продаж и себеса


def get_best_keyword(keywords: list[CalculatedKeyword]) -> CalculatedKeyword | None:
    # TODO: Функция упала бы на Smoke-тесте при пустом списке ключевых слов и упала на полной фильтрации
    if not keywords:
        return None
    keywords = [kw for kw in keywords if kw.position >= 0]
    if not keywords:
        return None
    best_keyword = sorted(
        keywords, key=lambda x: x.rating or 0, reverse=True
    )[0]

    return best_keyword


async def clear_cards(need_nmids: list[int]) -> None:
    async with _sm(read_only=False) as session:
        stmt = select(WBCard).where(WBCard.nmid.notin_(need_nmids))
        result = await session.execute(stmt)
        wb_cards: list[WBCard] = list(result.unique().scalars().all())
        await session.delete(wb_cards)
        await session.commit()


async def clear_keywords(need_keywords: list[str]) -> None:
    async with _sm(read_only=False) as session:
        stmt = select(KeywordSetting).where(KeywordSetting.text.notin_(need_keywords))
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = list(result.unique().scalars().all())
        await session.delete(keyword_settings)
        await session.commit()


async def get_expired_cabinets(session: AsyncSession) -> list[WBCabinet]:
    delete_expired_time = datetime.now() - timedelta(days=30)
    stmt = (
        select(WBCabinet)
        .options(selectinload(WBCabinet.adv_settings))
        .where(WBCabinet.expiration_time < delete_expired_time)
    )
    result = await session.execute(stmt)
    wb_cabinets: list[WBCabinet] = list(result.unique().scalars().all())
    return wb_cabinets


async def clear_cards_in_db(nmids: list[int]) -> None:
    async with _sm(read_only=False) as session:
        stmt = select(WBCard).where(WBCard.nmid.notin_(nmids))
        result = await session.execute(stmt)
        wb_cards: list[WBCard] = list(result.unique().scalars().all())
        for card in wb_cards:
            await session.delete(card)
            await session.commit()


async def get_sum_bot_balance_from_wb_wb_user_cabinet_original_id(
    shop_id: str,
) -> float | None:
    stmt = select(
        func.sum(coalesce(WBCabinet.balance, 0) + coalesce(WBCabinet.bonus, 0))
    ).where(WBCabinet.shop_id == shop_id)
    async with _sm() as session:
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# async def get_keywords_positions_dict_by_text(
#     adv_setting: AdvSetting, texts: list[str]
# ) -> dict[str, WBItemPosition]:
#     # Type ignore for untyped redis_manager call
#     positions = await redis_manager.get_keywords_positions(adv_setting, texts)  # type: ignore[no-untyped-call]
#     positions = [position for position in positions if position]
#     positions = {position.keyword_text: position for position in positions}
#     return positions


async def add_white_phrases(keywords: list[str], adv_setting_id: int) -> None:
    async with _sm(read_only=False) as session:
        adv = await session.get(AdvSetting, adv_setting_id)
        if adv is None:
            return
        for text in keywords:
            stmt = (
                select(KeywordSetting)
                .join(KeywordSetting.adv_setting)
                .where(
                    and_(KeywordSetting.text == text, AdvSetting.id == adv_setting_id)
                )
            )
            result = await session.execute(stmt)
            keyword_setting = result.scalar()
            if not keyword_setting:
                adv_keyword = AdvKeyword(
                    text=text,
                    adv_setting_id=adv_setting_id,
                    views=0,
                    clicks=0,
                    spend=0,
                    date=datetime.now().date(),  # noqa
                )

                keyword_setting = KeywordSetting(
                    text=text,
                    adv_setting_id=adv_setting_id,
                )
                keyword_setting.adv_keywords.append(adv_keyword)
                session.add(keyword_setting)
            keyword_setting.hard_status = 2
            _ = sync_keyword_setting_mode_for_v3(
                keyword_setting,
                bot_active=adv.bot_active,
                hard_status_override=2,
                adv_strategy=adv.strategy,
            )
        await session.commit()


async def add_fixed_phrases(keywords: list[str], adv_setting_id: int) -> None:
    async with _sm(read_only=False) as session:
        adv = await session.get(AdvSetting, adv_setting_id)
        if adv is None:
            return
        for text in keywords:
            stmt = (
                select(KeywordSetting)
                .join(KeywordSetting.adv_setting)
                .where(
                    and_(KeywordSetting.text == text, AdvSetting.id == adv_setting_id)
                )
            )
            result = await session.execute(stmt)
            keyword_setting = result.scalar()
            if not keyword_setting:
                adv_keyword = AdvKeyword(
                    text=text,
                    adv_setting_id=adv_setting_id,
                    views=0,
                    clicks=0,
                    spend=0,
                    date=datetime.now().date(),  # noqa
                )

                keyword_setting = KeywordSetting(
                    text=text,
                    adv_setting_id=adv_setting_id,
                )
                keyword_setting.adv_keywords.append(adv_keyword)
                session.add(keyword_setting)
            keyword_setting.hard_status = ALWAYS_ON
            keyword_setting.relevant = True
            _ = sync_keyword_setting_mode_for_v3(
                keyword_setting,
                bot_active=adv.bot_active,
                hard_status_override=ALWAYS_ON,
                adv_strategy=adv.strategy,
            )
        await session.commit()


async def update_black_phrases(adv_setting_id: int, keywords: list[str]) -> None:
    async with _sm(read_only=True) as session:
        adv = await session.get(AdvSetting, adv_setting_id)
        if adv is None:
            return
    manager = RelevantPhraseManager(adv)
    await manager.update_black_phrases(keywords)

#
# async def check_by_black_list_template(keyword_text: str, adv_setting_id: int) -> bool:
#     black_keywords = await redis_manager.get_black_phrases(adv_setting_id)
#     keyword_text_lower = keyword_text.lower().strip()
#
#     for black_phrase in black_keywords:
#         black_phrase_text = black_phrase.lower().strip()
#         if "'" in black_phrase_text or '"' in black_phrase_text:
#             black_phrase_text = black_phrase_text.replace("'", "''").replace('"', '""')
#             if black_phrase_text == keyword_text_lower:
#                 return True
#         else:
#             if black_phrase_text in keyword_text_lower:
#                 return True
#     return False


async def reset_black_phrases(adv_setting_id: int) -> None:
    async with _sm(read_only=True) as session:
        adv = await session.get(AdvSetting, adv_setting_id)
        if adv is None:
            return
    manager = RelevantPhraseManager(adv)
    await manager.update_black_phrases([])


async def update_relevant_phrases_templates(
    adv_setting_id: int, keywords: list[str]
) -> None:
    async with _sm(read_only=True) as session:
        adv = await session.get(AdvSetting, adv_setting_id)
        if adv is None:
            return
    manager = RelevantPhraseManager(adv)
    await manager.update_relevant_phrases_templates(keywords)


async def reset_relevant_phrases_templates(adv_setting_id: int) -> None:
    await update_relevant_phrases_templates(adv_setting_id, [])


async def add_relevant_phrases(keywords: list[str], adv_setting_id: int) -> None:
    async with _sm(read_only=False) as session:
        adv = await session.get(AdvSetting, adv_setting_id)
        if adv is None:
            return
        for text in keywords:
            stmt = (
                select(KeywordSetting)
                .join(KeywordSetting.adv_setting)
                .where(
                    and_(KeywordSetting.text == text, AdvSetting.id == adv_setting_id)
                )
            )
            result = await session.execute(stmt)
            keyword_setting = result.scalar()
            created = False
            if keyword_setting:
                keyword_setting.relevant = True
            else:
                created = True
                adv_keyword = AdvKeyword(
                    text=text,
                    adv_setting_id=adv_setting_id,
                    views=0,
                    clicks=0,
                    spend=0,
                    date=datetime.now().date(),  # noqa
                )

                keyword_setting = KeywordSetting(
                    text=text,
                    adv_setting_id=adv_setting_id,
                )
                keyword_setting.relevant = True
                keyword_setting.adv_keywords.append(adv_keyword)
                session.add(keyword_setting)
            # Sync mode только при смене hard_status (ЧС→авто) или для нового ключа;
            # иначе сбрасывается лестница V3 у БС (OPTIMUM/MAX → MIN_CPA).
            if keyword_setting.hard_status == 0:
                keyword_setting.hard_status = 1
                _ = sync_keyword_setting_mode_for_v3(
                    keyword_setting,
                    bot_active=adv.bot_active,
                    hard_status_override=1,
                    adv_strategy=adv.strategy,
                )
            elif created:
                _ = sync_keyword_setting_mode_for_v3(
                    keyword_setting,
                    bot_active=adv.bot_active,
                    hard_status_override=1,
                    adv_strategy=adv.strategy,
                )
        await session.commit()


async def get_active_search_advs() -> list[AdvSetting]:
    pattern = r"<!-\[(\d+)\]-!>"
    stmt = select(AdvSetting).where(
        # Проверяем, что name содержит паттерн <!-[цифры]-!>
        AdvSetting.name.op("~")(pattern),
        AdvSetting.bot_active.is_(True),
        AdvSetting.active_status == "started",
    )
    async with _sm() as session:
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()
    return list(adv_settings)


async def get_all_active_shop_ids_with_active_advs() -> list[str]:
    stmt = (
        select(WBCabinet.shop_id)
        .join(WBCabinet.adv_settings)
        .where(AdvSetting.bot_active)
    )
    async with _sm() as session:
        result = await session.execute(stmt)
        shop_ids = result.scalars().all()
    return list(shop_ids)


async def get_all_shop_ids() -> list[str]:
    stmt = select(WBCabinet.shop_id).distinct()
    async with _sm() as session:
        result = await session.execute(stmt)
        shop_ids = result.scalars().all()
    return list(shop_ids)


async def get_active_adv_ids_for_shop(shop_id: str) -> Sequence[int]:
    stmt = (
        select(AdvSetting)
        .distinct()
        .join(AdvSetting.wb_cabinet)
        .where(WBCabinet.shop_id == shop_id, AdvSetting.bot_active.is_(True))
        .options(
            load_only(
                AdvSetting.adv_id, AdvSetting.name, AdvSetting._search_adv_id # pyright: ignore # noqa
            )  # noqa
        )
    )
    async with _sm() as session:
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = list(result.scalars().all())
    adv_ids: list[int] = []
    for adv in adv_settings:
        adv_ids.append(adv.adv_id)
        if search_adv_id := adv.search_adv_id:
            adv_ids.append(search_adv_id)

    return adv_ids



async def is_adv_in_favorites(
    adv_setting_original_id: int, user_original_id: int
) -> bool:
    stmt = select(favorite_advs_association).where(
        and_(
            favorite_advs_association.c.user_id == user_original_id,
            favorite_advs_association.c.adv_id == adv_setting_original_id,
        )
    )
    async with _sm() as session:
        result = await session.execute(stmt)
        return result.first() is not None


# def __calculate_version(position: WBItemPosition) -> int:
#     if position.timestamp is None:
#         return int(datetime.now().timestamp())
#     return int(position.timestamp.timestamp())

#
# async def get_avg_base_positions(
#     nmid: int, start_date: str, end_date: str
# ) -> list[WBItemPosition]:
#     query = """
#     SELECT toDate(timestamp) as date,
#        text,
#        AVG(base_position) as avg_base_position
# FROM default_db.wbitemposition
# WHERE nmid = %(nmid)s
#   AND timestamp >= toDateTime(%(start_date)s)
#   AND timestamp <= toDateTime(%(end_date)s)
# GROUP BY date, text
# ORDER BY date, text
#
#     """  # Removed the semicolon
#
#     parameters = {"nmid": nmid, "start_date": start_date, "end_date": end_date}
#
#     async with get_clickhouse_client() as client:
#         result = await client.query(query, parameters=parameters)
#         result = result.result_rows
#         return [
#             WBItemPosition(nmid=nmid, position=row[1], timestamp=row[0])
#             for row in result  # type: ignore[attr-defined]
#         ]

#
# async def add_positions_to_clickhouse(positions: list[WBItemPosition]) -> None:
#     async with get_clickhouse_client() as client:
#         for position in positions:
#             try:
#                 # Генерация версии и подготовка timestamp
#                 version = __calculate_version(position)
#                 timestamp_str = position.timestamp.strftime("%Y-%m-%d %H:%M:%S")
#
#                 # Всегда вставляем новые данные
#                 query_insert = f"""
#                 INSERT INTO default_db.wbitemposition (
#                     nmid,
#                     text,
#                     promo_position,
#                     base_position,
#                     cpm,
#                     adv_type,
#                     timestamp,
#                     version
#                 )
#                 VALUES (
#                     {position.nmid},
#                     '{position.keyword_text.replace("'", "''")}',  # Экранирование одинарных кавычек
#                     {position.position if position.position else 0},
#                     {position.position if position.position else 0},
#                     {0},
#                     {int(position.adv_type) if position.adv_type else 0},
#                     '{timestamp_str}',
#                     {version}
#                 )
#                 """
#                 await client.query(query_insert)
#                 logger.debug(f"Добавлена запись для nmid={position.nmid}")
#
#             except Exception as e:
#                 logger.error(
#                     f"Ошибка при обработке позиции nmid={position.nmid}: {e}",
#                     exc_info=True,
#                 )

#
# async def get_keyword_positions_from_click_house(nmid: int) -> list[WBItemPosition]:
#     query = f"""
#     SELECT
#         text,
#         toDate(timestamp) AS day,
#         AVG(promo_position) AS avg_promo_position,
#         AVG(base_position) AS avg_base_position,
#         AVG(cpm) AS avg_cpm
#     FROM default_db.wbitemposition
#     WHERE nmid = {nmid}
#     GROUP BY text, day
#     ORDER BY day
#     """
#
#     async with get_clickhouse_client() as client:
#         result = await client.query(query)
#         positions_rows = result.result_rows
#     positions: list[WBItemPosition] = []
#     for row in positions_rows:
#         position = WBItemPosition()
#         position.nmid = nmid
#         position.keyword_text = row[0]
#         avg_promo = row[2] if row[2] else 0
#         avg_base = row[3] if row[3] else 0
#         position.position = int(avg_base or avg_promo or 6000)
#         position.timestamp = datetime.combine(row[1], datetime.min.time())
#         positions.append(position)
#
#     return positions


async def set_last_full_stat_update(adv_id: int, timestamp: datetime) -> None:
    await redis_manager.set_last_full_stat_update(adv_id, timestamp)


async def get_last_full_stat_update(adv_id: int) -> datetime | None:
    return await redis_manager.get_last_full_stat_update(adv_id)


async def get_all_keywords_from_ch(last_days: int = 7) -> set[str]:
    ch_query = """
    SELECT DISTINCT norm_query FROM default_db.mv_clusters_daily_agg
    WHERE date >= today() - %(last_days)s
    """
    async with anti_ch_crash_semaphore:
        async with get_clickhouse_client() as client:
            result = await client.query(ch_query, parameters={"last_days": last_days})
            keywords = result.result_rows
    return set([keyword[0] for keyword in keywords if keyword])


async def get_cpm(auto_adv: AdvSetting) -> float | None:
    # CPM из парсинга больше недоступен, используем только настройки кампаний
    # Проверяем, есть ли CPM из аукциона
    auction_adv_id: int | None = auto_adv.search_adv_id
    cpm_from_auction = None
    if auction_adv_id:
        stmt = (
            select(AdvSetting)
            .options(load_only(AdvSetting.cpm))
            .where(AdvSetting.adv_id == auction_adv_id)
        )
        async with _sm() as session:
            result = await session.execute(stmt)
            auction_adv: AdvSetting | None = result.scalar_one_or_none()
            if auction_adv:
                cpm_from_auction = auction_adv.cpm

    # CPM из настроек рекламного объявления
    cpm_from_auto = auto_adv.cpm
    cpm_values = [cpm for cpm in [cpm_from_auction, cpm_from_auto] if cpm is not None]

    if not cpm_values:
        return None

    return max(cpm_values)


@inject
async def update_advs_data_from_wb_to_pg(
    wb_api: WBApi,
    *,
    auto_recommendations_bid_cache_manager: ShopDataUpdater.AutoRecommendationsBidCacheManager | None = None,
    redis_client_wrapper: RedisClient = Provide["redis_client_wrapper"],
) -> None:
    """Обновить кампании из WB в PG и заполнить Redis-кэш ставок полок.

    Если cache manager не передан явно (например, из adv-creator tasks),
    используется дефолтный `RedisAutoRecommendationsBidValueManager` через DI,
    чтобы shelf increments не попадали в `no_bid` до следующего shop-runner sync.
    """
    bid_cache_manager = auto_recommendations_bid_cache_manager
    if bid_cache_manager is None:
        bid_cache_manager = RedisAutoRecommendationsBidValueManager(
            redis_client=redis_client_wrapper,
        )
    shop_data_updater = ShopDataUpdater(
        wb_api,
        auto_recommendations_bid_cache_manager=bid_cache_manager,
    )
    _ = await shop_data_updater.update_advs_data()
    return None
