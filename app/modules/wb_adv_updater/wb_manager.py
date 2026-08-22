import asyncio
import csv
import datetime
import io
import logging

from aiohttp import ClientSession
from clickhouse_connect.driver.external import ExternalData
from sqlalchemy import exists, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
)
from app.modules.common_slaves.wildberries.wb_api import WBApi

from app.my_types import KeywordStat
from app.utils import redis_manager, text_cleaner
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.session_maker import get_async_session_maker
from .wb_adv_api import WBAdvAPI
from ..billing import AdvPayment
from ..common_slaves.wildberries import super_cabinet_manager
from ..common_slaves.wildberries.models.wb_cabinet import WBCabinet
from ..common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from ..relevant_phrase_manager import RelevantPhraseManager
from ..relevant_phrase_manager.not_relevante_template import NotRelevantTemplate
from ..shop_runner.service_manager.services.v3_status_mode_sync import (
    sync_keyword_setting_mode_for_v3,
)
from ..wb_update_state_manager import KeywordStatUpdateState
from ...core.wb_api.exceptions import ApiForbiddenError
from ...core.wb_api.mixins.adv import MinCPMData
from ...utils.ch_semaphore import anti_ch_crash_semaphore

logger = logging.getLogger(__name__)

sm = get_async_session_maker

keywords_hashs_in_neo = set()


def get_count_advs_for_wb_cabinet(
    wb_cabinet: WBCabinet, adv_settings: list[AdvSetting]
) -> int:
    advs_for_wb_cabinet = [
        adv_setting
        for adv_setting in adv_settings
        if adv_setting.wb_cabinet_id == wb_cabinet.id
    ]
    return len(advs_for_wb_cabinet)


async def check_adv_payment(
    session: AsyncSession, adv_setting: AdvSetting, current_date: datetime.date
) -> bool:
    """Проверяет наличие платежа для настройки рекламы на указанную дату."""
    adv_payment_check_stmt = select(
        exists().where(
            and_(
                AdvPayment.adv_setting_id == adv_setting.id,
                AdvPayment.date == current_date,
            )
        )
    )

    result = await session.execute(adv_payment_check_stmt)
    return result.scalar()


# async def graph_vector_update() -> None:
#     graph_updater = GraphUpdater()
#     length = 2**4
#     await graph_updater.update_graph_run(length)
#     await asyncio.sleep(1)
#     return


# async def update_vectors_update_in_graph() -> None:
#     while True:
#         try:
#             await graph_vector_update()
#         except Exception as exc:
#             logger.error(f"Ошибка векторизации {exc}", exc_info=True)
#             del exc
#         await asyncio.sleep(0)



async def insert_or_update_keywords(keyword_stats, adv_id: int) -> None:
    new_version = int(datetime.datetime.now().timestamp())

    buffer = io.StringIO()
    writer = csv.writer(
        buffer,
        delimiter=",",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )

    for kw in keyword_stats:
        try:
            text_val = (
                text_cleaner.clear(kw.text or "")
                .strip()
                .replace("\n", " ")
                .replace("\r", " ")
            )
            if not text_val:
                continue
            # TODO: Решить проблему со спамом в чате
            date_val = kw.date
            if isinstance(date_val, (datetime.datetime, datetime.date)):
                date_str = date_val.strftime("%Y-%m-%d")
            else:
                continue

            writer.writerow(
                [
                    adv_id,
                    text_val,
                    date_str,
                    int(kw.clicks),
                    int(kw.views),
                    float(kw.spend),
                    new_version,
                ]
            )
        except Exception as e:
            logger.warning("Ошибка при подготовке CSV строки: %s", e, exc_info=True)
            continue

    csv_data = buffer.getvalue()
    if not csv_data.endswith("\n"):
        csv_data += "\n"

    csv_bytes = csv_data.encode("utf-8")

    # Важно: имя таблицы в external_data должно совпадать с тем, что используется в запросе
    ext_data = ExternalData(
        data=csv_bytes,
        file_name="data.csv",
        structure="adv_id UInt64, text String, date Date, clicks UInt32, views UInt32, spend Float64, version UInt64",
        fmt="CSV",
    )

    # ИСПРАВЛЕНИЕ: убираем input() из запроса, ссылаемся на external table по имени файла
    query = """
    INSERT INTO default_db.advkeyword_new (adv_id, text, date, clicks_state, views_state, spend_state)
    SELECT
        adv_id,
        text,
        toDate(date) AS date,
        argMaxState(clicks, version) AS clicks_state,
        argMaxState(views, version) AS views_state,
        argMaxState(spend, version) AS spend_state
    FROM data
    GROUP BY adv_id, text, date
    """
    async with anti_ch_crash_semaphore:
        async with get_clickhouse_client() as client:
            await client.query(query, external_data=ext_data) # noqa

    logger.debug(f"Inserted/updated {len(keyword_stats)} rows into advkeyword_new")


async def update_keywords_stat_in_click_house(
    keyword_stats: list[KeywordStat],
    adv_id: int,
) -> None:
    if keyword_stats:
        await insert_or_update_keywords(
            keyword_stats,
            adv_id,
        )


async def get_existing_keyword_settings(adv_setting_id) -> set[str]:
    async with sm() as session:
        stmt = select(KeywordSetting).where(
            KeywordSetting.adv_setting_id == adv_setting_id
        )
        result = await session.execute(stmt)
        existing_keyword_settings: list[KeywordSetting] = result.scalars().all()
    return {ks.text for ks in existing_keyword_settings}


async def update_all_keyword_data(
    wb_api: WBApi,
    adv_setting,
    wb_cabinet: WBCabinet,
):
    shop_id = wb_cabinet.shop_id
    try:
        await common_keyword_stat_update(adv_setting, wb_api)
    except ApiForbiddenError:
        logger.warning(f"Нет доступов для обновления данных магазина: {shop_id}")

        return
    except Exception as exc:
        logger.error(
            "Ошибка обновления статистики ключевых слов для магазина: %s, кампании: %s",
            shop_id,
            adv_setting.id,
            exc_info=True,
        )
        raise exc
    return


async def update_all_keywords_on_wb(client_session: ClientSession) -> None:
    from app.modules.common_slaves.wildberries.wb_api import WBApi

    update_tasks: dict[int, asyncio.Task[None]] = {}
    while True:
        async with sm() as session:
            stmt = select(AdvSetting).where(AdvSetting.bot_active)
            result = await session.execute(stmt)
            adv_settings: list[AdvSetting] = result.scalars().all()
            # TODO: Заккомитил фильтр по adv_id и это попало в продакшен. Сделать текст во избежание проблем. СРОЧНО!!!
        for adv_setting in adv_settings:
            if adv_setting.id not in update_tasks:
                wb_cabinet_id = adv_setting.wb_cabinet_id
                access: WBCabinetAccess = (
                    await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
                )
                if not access:
                    logger.error(f"Нет доступа к кабинету {wb_cabinet_id}")
                    continue
                wb_api = WBApi(access, client_session)
                wb_cabinet = access.wb_cabinet
                assert wb_cabinet
                # TODO: Перенести это все в магазины и переделать под таск-группы
                task = asyncio.create_task(
                    update_all_keyword_data(wb_api, adv_setting, wb_cabinet=wb_cabinet)
                )
                update_tasks[adv_setting.id] = task
            else:
                if update_tasks[adv_setting.id].done():
                    if update_tasks[adv_setting.id].exception():
                        logger.error(
                            adv_setting.id,
                            update_tasks[adv_setting.id].exception(),  # noqa
                        )
                    del update_tasks[adv_setting.id]
            await asyncio.sleep(0)


async def update_clusters_for_adv(adv: AdvSetting, wb_api: WBApi):
    try:
        clusters = await wb_api.advert.get_clusters_for_adv(adv)
        clusters = clusters["clusters"]
        if not clusters:
            return
        for cluster in clusters:
            cluster_name = cluster["cluster"].strip().lower()
            keywords = cluster["keywords"]
            for keyword_text in keywords:
                keyword_text = keyword_text.strip().lower()
                await redis_manager.set_keyword_cluster(keyword_text, cluster_name)
    except Exception as e:
        logger.debug(f"Error getting clusters for adv {adv.id}: {e}", exc_info=True)
        del e
        return


async def common_keyword_stat_update(adv_setting: AdvSetting, wb_api):
    auto_adv_id = adv_setting.adv_id
    auction_adv_id = adv_setting.search_adv_id
    keywords_from_auto: list[KeywordStat] = []
    try:
        keywords_from_auto = await wb_api.advert.get_keywords_stat(auto_adv_id)
        await update_keywords_stat_in_click_house(
            keywords_from_auto,
            auto_adv_id,
        )

    except ApiForbiddenError as exc:
        raise exc
    except Exception as exc:
        logger.error(
            f"Ошибка получения статистики по ключевым словам для кампании: {adv_setting.name}, "
            f"shop_id: {wb_api.wb_access.wb_cabinet.shop_id}, {exc}",
            exc_info=True,
        )
        del exc
    keywords_from_search_adv: list[KeywordStat] = []
    try:
        if auction_adv_id:
            keywords_from_search_adv = await wb_api.advert.get_keywords_stat(
                auction_adv_id
            )
            await update_keywords_stat_in_click_house(
                keywords_from_search_adv,
                auction_adv_id,
            )
    except Exception as exc:
        keywords_from_search_adv = []
        logger.error(
            "Ошибка получения статистики по ключевым словам для %s, %s",
            adv_setting.name,
            exc,
        )
        del exc

    if not keywords_from_auto and not keywords_from_search_adv:
        logger.debug(f"Пустой список ключевых слов для {adv_setting.adv_id}")
        return

    text_to_keyword_from_auto: dict[str, KeywordStat] = {
        kw.text + ":" + str(kw.date): kw for kw in keywords_from_auto
    }
    for kw in keywords_from_search_adv:
        key: str = kw.text + ":" + str(kw.date)
        if key not in text_to_keyword_from_auto:
            text_to_keyword_from_auto[key] = kw
        else:
            text_to_keyword_from_auto[key].views += kw.views # pyright: ignore
            text_to_keyword_from_auto[key].clicks += kw.clicks # pyright: ignore
            text_to_keyword_from_auto[key].spend += kw.spend # pyright: ignore
    full_stat: list[KeywordStat] = list(text_to_keyword_from_auto.values())

    full_stat_keywords: list[KeywordStat] = full_stat

    logger.debug(
        "Получено %s ключевых слов для %s", len(full_stat_keywords), adv_setting.name
    )
    texts_for_adv_setting: set[str] = {keyword.text for keyword in full_stat_keywords}
    clusters: set[str] = set()
    for text_for_adv in texts_for_adv_setting:
        try:
            cluster_name, _ = await redis_manager.get_cluster_and_preset(text_for_adv)
        except:  # noqa
            logger.error("Не удалось получить кластер")
            cluster_name = None

        if cluster_name:
            clusters.add(cluster_name)

    texts_for_adv_setting.update(clusters)
    existing_keyword_settings: set[str] = await get_existing_keyword_settings(adv_setting.id)
    new_keywords: set[str] = texts_for_adv_setting - existing_keyword_settings

    # Преобразование ключевых слов в объекты KeywordSetting
    keyword_settings = [
        KeywordSetting(text=keyword, adv_setting_id=adv_setting.id)
        for keyword in new_keywords
    ]
    relevant_phrase_manager = RelevantPhraseManager(adv_setting)
    template_data = await relevant_phrase_manager.get_relevant_template_data()

    not_rel_templator = NotRelevantTemplate(template_data)

    try:
        async with sm(read_only=False) as session:
            # Обработка данных порциями
            for keyword in keyword_settings:
                text = keyword.text
                if not not_rel_templator.is_relevant(text):
                    keyword.hard_status = 0
                _ = sync_keyword_setting_mode_for_v3(
                    keyword,
                    bot_active=adv_setting.bot_active,
                    hard_status_override=int(keyword.hard_status),
                    adv_strategy=adv_setting.strategy,
                )
                session.add(keyword)
            await session.commit()
    except Exception as exc:
        logger.error(
            "Ошибка добавления ключевых слов в базу данных: %s", exc, exc_info=True
        )
        raise exc

    keyword_stat_update_state = KeywordStatUpdateState()

    await keyword_stat_update_state.set_one(adv_setting.adv_id)

    return


class MessageCounter:
    _last_time_send = None
    _period = datetime.timedelta(minutes=10)

    def add_send(self):
        time = datetime.datetime.now()
        self._last_time_send = time

    def check_last_time(self):
        now = datetime.datetime.now()
        if self._last_time_send is None:
            return True
        if now - self._last_time_send > self._period:  # noqa
            return True


message_counter = MessageCounter()


async def update_wb_config_data(client_session: ClientSession) -> None:
    access = await super_cabinet_manager.get_common_access(client_session)
    wb_api = WBAdvAPI(access, client_session)
    min_cpm_data: MinCPMData = await wb_api.get_min_cpm_adv_data()
    await redis_manager.set_min_cpm_data(min_cpm_data)

