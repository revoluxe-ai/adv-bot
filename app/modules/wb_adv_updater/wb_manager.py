import asyncio
import datetime
import logging
from typing import List

from aiohttp import ClientSession
from sqlalchemy import exists, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.common_slaves.wildberries.models import (
    WBBalancePayment,
    WBBonusPayment,
)
from app.modules.common_slaves.wildberries.models import WBCabinet
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_adv_updater.models import AdvPayment
from app.my_types import KeywordStat
from app.utils import redis_manager
from app.utils.NeoDataScience.driver import DataScience
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.session_maker import get_async_session_maker
from .ML import Predictor
from .data_setter import DataSetter
from .graph_vector_updater import GraphUpdater
from .wb_adv_api import WBAdvAPI
from ..common_slaves.wildberries import super_cabinet_manager
from ..common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from ..relevant_phrase_manager import RelevantPhraseManager
from ..relevant_phrase_manager.not_relevante_template import NotRelevantTemplate
from ..wb_update_state_manager import KeywordStatUpdateState
from ...core.wb_api.exceptions import ApiForbiddenError
from ...core.wb_api.mixins.adv import MinCPMData
from ...utils.pricer.pricer import Pricer

logger = logging.getLogger(__name__)

gds = DataScience()

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
            AdvPayment.adv_setting_id == adv_setting.id, AdvPayment.date == current_date
        )
    )

    result = await session.execute(adv_payment_check_stmt)
    return result.scalar()


async def process_payment_for_advs() -> None:
    current_date = datetime.datetime.now().date()
    async with sm(read_only=False) as session:
        stmt = (
            select(AdvSetting)
            .options(
                joinedload(AdvSetting.payments),
                joinedload(AdvSetting.wb_cabinet).selectinload(
                    WBCabinet.balance_payments
                ),
                joinedload(AdvSetting.wb_cabinet).selectinload(
                    WBCabinet.bonus_payments
                ),
            )
            .where(
                or_(
                    AdvSetting.bot_active == True,
                    AdvSetting.auto_update_white_list == True,
                    AdvSetting.auto_update_target_place == True,
                )
            )
        )
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.unique().scalars().all()
        pricer = Pricer()
        for adv_setting in adv_settings:
            if await check_adv_payment(session, adv_setting, current_date):
                continue
            wb_cabinet: WBCabinet = adv_setting.wb_cabinet
            shop_id: str = str(wb_cabinet.shop_id)
            PRICE_FOR_SHOP_FOR_DAY = await pricer.get_price_for_day_for_shop(shop_id)
            count_advs_for_wb_cabinet: int = get_count_advs_for_wb_cabinet(
                wb_cabinet, adv_settings
            )
            PRICE_FOR_ADV_FOR_DAY = PRICE_FOR_SHOP_FOR_DAY / count_advs_for_wb_cabinet
            # Используем гибридные свойства вместо прямого доступа к полям
            calculated_bonus = wb_cabinet.calculated_bonus
            calculated_balance = wb_cabinet.calculated_balance

            # Сначала проверяем наличие средств
            if calculated_bonus >= PRICE_FOR_ADV_FOR_DAY:
                # Создаем платеж и запись списания бонусов
                payment = AdvPayment(date=current_date, amount=PRICE_FOR_ADV_FOR_DAY)
                adv_setting.payments.append(payment)

                bonus_payment = WBBonusPayment(
                    wb_cabinet_id=wb_cabinet.id,
                    amount=-PRICE_FOR_ADV_FOR_DAY,  # Отрицательное значение для списания
                    description=f"Списание за рекламную кампанию {adv_setting.adv_id}",
                    operation_type="subtract",
                )
                session.add(bonus_payment)
            elif calculated_balance >= PRICE_FOR_ADV_FOR_DAY:
                # Создаем платеж и запись списания с баланса
                payment = AdvPayment(date=current_date, amount=PRICE_FOR_ADV_FOR_DAY)
                adv_setting.payments.append(payment)

                balance_payment = WBBalancePayment(
                    wb_cabinet_id=wb_cabinet.id,
                    amount=-PRICE_FOR_ADV_FOR_DAY,  # Отрицательное значение для списания
                    description=f"Списание за рекламную кампанию {adv_setting.adv_id}",
                )
                session.add(balance_payment)
            else:
                # Если недостаточно средств, деактивируем бота
                adv_setting.bot_active = False
                adv_setting.auto_update_white_list = False
                adv_setting.auto_update_target_place = False

            await session.commit()


async def graph_vector_update() -> None:
    graph_updater = GraphUpdater()
    length = 2**4
    await graph_updater.update_graph_run(length)
    await asyncio.sleep(1)
    return


async def update_vectors_update_in_graph() -> None:
    while True:
        try:
            await graph_vector_update()
        except Exception as exc:
            logger.error(f"Ошибка векторизации {exc}", exc_info=True)
            del e
        await asyncio.sleep(0)


async def update_vectors_in_redis() -> None:
    await gds.update_vectors_in_redis()


async def insert_or_update_keywords(keyword_stats, adv_id, table_name: str):
    # Подготовка данных для вставки
    new_version = int(datetime.datetime.now().timestamp())
    data_to_insert = []
    for kw in keyword_stats:
        date_time = datetime.datetime.combine(
            kw.date, datetime.datetime.min.time()
        )  # просто добавляем время к дате
        data_to_insert.append(
            [kw.text, date_time, adv_id, kw.views, kw.clicks, kw.spend, new_version]
        )
    async with get_clickhouse_client() as client:
        await client.insert(
            table=f"default_db.{table_name}",
            data=data_to_insert,
            column_names=[
                "text",
                "date",
                "adv_id",
                "views",
                "clicks",
                "spend",
                "version",
            ],
        )


async def update_keywords_stat_in_click_house(
    keyword_stats: List[KeywordStat], adv_id: int, table_name: str
) -> None:
    if keyword_stats:
        await insert_or_update_keywords(keyword_stats, adv_id, table_name)


async def get_existing_keyword_settings(adv_setting_id) -> set[str]:
    async with sm() as session:
        stmt = select(KeywordSetting).where(
            KeywordSetting.adv_setting_id == adv_setting_id
        )
        result = await session.execute(stmt)
        existing_keyword_settings: list[KeywordSetting] = result.scalars().all()
    return {ks.text for ks in existing_keyword_settings}


async def update_predict_ctr() -> None:
    while True:
        logger.debug("Начинаю прогноз CTR")
        predictor = Predictor()
        await predictor.predict_ctr_for_keywords()


async def update_all_keyword_data(
    wb_api: WBApi,
    adv_setting,
    wb_cabinet: WBCabinet,
):
    shop_id = wb_cabinet.shop_id
    try:
        await common_keyword_stat_update(adv_setting, wb_api)
    except ApiForbiddenError:
        logger.error(f"Нет доступов для обновления данных магазина: {shop_id}")

        return
    except Exception as exc:
        logger.error("Ошибка обновления статистики ключевых слов", exc_info=True)
        raise exc
    try:
        keywords = await data_manager.get_good_bad_phrases(adv_setting)
        data_setter = DataSetter(wb_api)
        await data_setter.update_minus_keywords_in_adv(
            adv_setting, wb_cabinet, keywords
        )
    except Exception as exc:
        logger.error("Ошибка установки активности фраз", exc_info=True)
        raise exc
    return


async def update_all_keywords_on_wb(client_session: ClientSession) -> None:
    from app.modules.common_slaves.wildberries.api import WBApi

    update_tasks: dict[int, asyncio.Task] = {}
    while True:
        async with sm() as session:
            stmt = select(AdvSetting).where(AdvSetting.bot_active)
            result = await session.execute(stmt)
            adv_settings: list[AdvSetting] = result.scalars().all()
            for adv_setting in adv_settings:
                if adv_setting.id not in update_tasks:
                    wb_cabinet_id = adv_setting.wb_cabinet_id
                    access: WBCabinetAccess = (
                        await super_cabinet_manager.get_access_for_wb_cabinet(
                            wb_cabinet_id
                        )
                    )
                    if not access:
                        logger.error(f"Нет доступа к кабинету {wb_cabinet_id}")
                        continue
                    wb_api = WBApi(access, client_session)
                    task = asyncio.create_task(
                        update_all_keyword_data(
                            wb_api, adv_setting, wb_cabinet=access.wb_cabinet
                        )
                    )
                    update_tasks[adv_setting.id] = task
                else:
                    if update_tasks[adv_setting.id].done():
                        if update_tasks[adv_setting.id].exception():
                            logger.error(
                                f"Ошибка обновления ключей  для shop_id: {access.wb_cabinet.shop_id} "
                                f"Кампания: {adv_setting.adv_id} "
                                f" {update_tasks[adv_setting.id].exception()}",
                                exc_info=True,
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
    try:
        keywords_from_auto: list[KeywordStat] = await wb_api.advert.get_keywords_stat(
            auto_adv_id
        )
        await update_keywords_stat_in_click_house(
            keywords_from_auto, auto_adv_id, "advkeyword"
        )

    except ApiForbiddenError as exc:
        raise exc
    except Exception as exc:
        keywords_from_auto = []
        logger.error(
            f"Ошибка получения статистики по ключевым словам для кампании: {adv_setting.name}, "
            f"shop_id: {wb_api.wb_access.wb_cabinet.shop_id}, {exc}",
            exc_info=True,
        )
        del exc
    try:
        if not auction_adv_id:
            keywords_from_search_adv = []
        else:
            keywords_from_search_adv = await wb_api.advert.get_keywords_stat(
                auction_adv_id
            )
            await update_keywords_stat_in_click_house(
                keywords_from_search_adv, auction_adv_id, "advkeyword"
            )
    except Exception as exc:
        keywords_from_search_adv = []
        logger.error(
            f"Ошибка получения статистики по ключевым словам для {adv_setting.name}, {exc}"
        )
        del exc

    if not keywords_from_auto and not keywords_from_search_adv:
        logger.debug(f"Пустой список ключевых слов для {adv_setting.adv_id}")
        return

    text_to_keyword_from_auto = {
        kw.text + ":" + str(kw.date): kw for kw in keywords_from_auto
    }
    for kw in keywords_from_search_adv:
        key = kw.text + ":" + str(kw.date)
        if key not in text_to_keyword_from_auto:
            text_to_keyword_from_auto[key] = kw
        else:
            text_to_keyword_from_auto[key].views += kw.views
            text_to_keyword_from_auto[key].clicks += kw.clicks
            text_to_keyword_from_auto[key].spend += kw.spend
    full_stat = list(text_to_keyword_from_auto.values())

    full_stat_keywords = full_stat

    logger.debug(
        f"Получено {len(full_stat_keywords)} ключевых слов для {adv_setting.name}"
    )
    texts_for_adv_setting = {keyword.text for keyword in full_stat_keywords}
    clusters = set()
    for text_for_adv in texts_for_adv_setting:
        try:
            cluster_name, _ = await redis_manager.get_cluster_and_preset(text_for_adv)
        except:
            logger.error("Не удалось получить кластер")
            cluster_name = None

        if cluster_name:
            clusters.add(cluster_name)

    texts_for_adv_setting.update(clusters)
    existing_keyword_settings = await get_existing_keyword_settings(adv_setting.id)
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
                session.add(keyword)
            await session.commit()
    except Exception as exc:
        logger.error(
            f"Ошибка добавления ключевых слов в базу данных: {exc}", exc_info=True
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
        if now - self._last_time_send > self._period:
            return True


message_counter = MessageCounter()


async def update_wb_config_data(client_session: ClientSession) -> None:
    access = await super_cabinet_manager.get_common_access(client_session)
    wb_api = WBAdvAPI(access, client_session)
    min_cpm_data: MinCPMData = await wb_api.get_min_cpm_adv_data()
    await redis_manager.set_min_cpm_data(min_cpm_data)


async def update_wb_config_data_run(client_session) -> None:
    while True:
        try:
            await update_wb_config_data(client_session)
        except Exception as exc:
            logger.error(f"Ошибка обновления данных {exc}", exc_info=True)
            raise exc
        finally:
            await asyncio.sleep(60 * 60)
