import logging
from typing import List
import faiss
import joblib
import numpy as np
from asyncpg import ProgramLimitExceededError
from sqlalchemy import not_, text
from sqlalchemy.exc import IntegrityError
from app.utils import redis_manager
from app.client_bot.bot import bot
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_adv_updater.models import AdvPayment
from .ABC_manager import AbcManager
from .data_setter import DataSetter
from .graph_vector_updater import GraphUpdater

from ..common_slaves.wildberries import super_cabinet_manager
from app.my_types import KeywordStat
from app.utils.NeoDataScience.driver import DataScience
from app.modules.common_slaves.wildberries.models import WBCabinet
import asyncio
from app.admin_bot.sender import messages
import pandas as pd
from sqlalchemy import and_
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.future import select
from .ML import Predictor
import datetime
from app.modules.common_slaves.wildberries.models import (WBUserCabinet,
                                                          AdvSetting,
                                                          KeywordSetting)

from app.modules.wb_adv_updater.models import GlobalCategorySetting
from app.utils.db.session_maker import get_async_session_maker
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from ..common_slaves.wildberries.exceptions import ApiForbiddenError
from ..common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from .shops_manager import rights_control
from ..wb_update_state_manager import KeywordStatUpdateState
from ...client_bot import const
from app.utils.click_house.client import get_clickhouse_client

logger = logging.getLogger(__name__)

gds = DataScience()

sm = get_async_session_maker

keywords_hashs_in_neo = set()


async def process_payment_for_auto_bidder():
    current_date = datetime.datetime.now().date()
    async with sm(read_only=False) as session:
        stmt = select(AdvSetting).options(
            joinedload(AdvSetting.payments),
            selectinload(AdvSetting.wb_cabinet)
        ).filter(
            and_(
                AdvSetting.bidder_active == True,
                AdvSetting.active_status == 'started',
                not_(AdvSetting.payments.any(and_(AdvPayment.date == current_date,
                                                  AdvPayment.type == 'auto_bidder')))

            )
        )

        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.unique().scalars().all()

        for adv_setting in adv_settings:
            wb_cabinet = adv_setting.wb_cabinet
            if not (bonus := wb_cabinet.bonus):
                bonus = 0
            if not (balance := wb_cabinet.balance):
                balance = 0
            if bonus >= const.AUTO_BIDDER_PRICE:
                payment = AdvPayment(date=current_date,
                                     type='auto_bidder')
                session.add(payment)
                adv_setting.payments.append(payment)
                wb_cabinet.bonus -= const.AUTO_BIDDER_PRICE
            elif balance > 0:
                payment = AdvPayment(date=current_date,
                                     type='auto_bidder')
                session.add(payment)
                adv_setting.payments.append(payment)
                wb_cabinet.balance -= const.AUTO_BIDDER_PRICE
            else:
                wb_cabinet.bonus = 0
                adv_setting.bidder_active = False
            await session.commit()
            await asyncio.sleep(0)



async def process_payment_for_parsing():
    current_date = datetime.datetime.now().date()
    async with sm(read_only=False) as session:
        stmt = select(AdvSetting).options(
            joinedload(AdvSetting.payments),
            selectinload(AdvSetting.wb_cabinet)
        ).filter(
            and_(
                AdvSetting.parsing_active == True,
                AdvSetting.active_status == 'started',
                not_(AdvSetting.payments.any(and_(AdvPayment.date == current_date,
                                                  AdvPayment.type == 'parsing')))

            )
        )

        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.unique().scalars().all()

        for adv_setting in adv_settings:
            wb_cabinet = adv_setting.wb_cabinet
            if not (bonus := wb_cabinet.bonus):
                bonus = 0
            if not (balance := wb_cabinet.balance):
                balance = 0
            if bonus >= const.PARSING_PRICE:
                payment = AdvPayment(date=current_date)
                adv_setting.payments.append(payment)
                wb_cabinet.bonus -= const.PARSING_PRICE
            elif balance > 0:
                payment = AdvPayment(date=current_date,
                                     type='parsing')
                adv_setting.payments.append(payment)
                wb_cabinet.balance -= const.PARSING_PRICE
            else:
                wb_cabinet.bonus = 0
                adv_setting.parsing_active = False
            await session.commit()
            await asyncio.sleep(0)


async def process_payment_for_advs():
    current_date = datetime.datetime.now().date()
    async with sm(read_only=False) as session:
        stmt = select(AdvSetting).options(
            joinedload(AdvSetting.payments),
            selectinload(AdvSetting.wb_cabinet)
        ).filter(
            and_(
                AdvSetting.bot_active == True,
                not_(AdvSetting.payments.any(AdvPayment.date == current_date)),
                AdvSetting.wb_cabinet.has(WBCabinet.expiration_time < current_date)
                # условие на истекший срок действия
            )
        )

        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.unique().scalars().all()

        for adv_setting in adv_settings:
            wb_cabinet = adv_setting.wb_cabinet
            if not (bonus := wb_cabinet.bonus):
                bonus = 0
            if not (balance := wb_cabinet.balance):
                balance = 0
            if bonus >= const.PRICE_FOR_ADV_FOR_DAY:
                payment = AdvPayment(date=current_date)
                adv_setting.payments.append(payment)
                wb_cabinet.bonus -= const.PRICE_FOR_ADV_FOR_DAY
            elif balance > 0:
                payment = AdvPayment(date=current_date)
                adv_setting.payments.append(payment)
                wb_cabinet.balance -= const.PRICE_FOR_ADV_FOR_DAY
            else:
                wb_cabinet.bonus = 0
                adv_setting.bot_active = False

            await session.commit()


async def graph_vector_update() -> None:
    graph_updater = GraphUpdater()
    length = 2 ** 4
    await graph_updater.update_graph_run(length)
    await asyncio.sleep(1)
    return



async def update_vectors_update_in_graph():
    while True:
        try:
            await graph_vector_update()
        except Exception as exc:
            logger.error(f'Ошибка векторизации {exc}', exc_info=True)
        await asyncio.sleep(0)




async def update_vectors_in_redis():
    await gds.update_vectors_in_redis()

async def shop_subscribe_control():
    while True:
        async with sm(read_only=False) as session:
            stmt = select(WBCabinet) \
                .options(
                selectinload(WBCabinet.wb_user_cabinets) \
                    .selectinload(WBUserCabinet.user),
                selectinload(WBCabinet.adv_settings)
            ) \
                .where(
                and_(
                    WBCabinet.expiration_time < datetime.datetime.now(),
                    WBCabinet.active == True,
                    WBCabinet.balance < 0
                )
            )
            result = await session.execute(stmt)
            wb_cabinets_expirated_and_active = result.scalars().all()
            for wb_cabinet in wb_cabinets_expirated_and_active:
                access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet.id)
                if not access:
                    logger.error('Нет доступа для кабинета')
                wb_api = WBApi(access)
                adv_settings: list[AdvSetting] = wb_cabinet.adv_settings
                for adv_setting in adv_settings:
                    if adv_setting.bot_active is True and adv_setting.active_status == 'started':
                        try:
                            await wb_api.advert.pause_company(adv_setting.adv_id)
                        except:
                            logger.error(f'Ошибка при попытке остановить кампанию {adv_setting.adv_id}')
                            continue
                        adv_setting.bot_active = False
                wb_cabinet.active = False
                await session.commit()
                wb_user_cabinets = wb_cabinet.wb_user_cabinets
                for wb_user_cabinet in wb_user_cabinets:
                    user = wb_user_cabinet.user
                    try:
                        await messages.ShopExpiredSubscriptionMessage(
                            bot,
                            wb_user_cabinet.user.user_telegram_id,
                            wb_user_cabinet)()
                        logger.debug(f'Сообщение о просроченной подписке отправлено для юзера {user.username}')
                    except Exception as exc:
                        logger.error(f'Ошибка при отправке сообщения о просроченной подписке '
                                     f'для юзера {user.username}: {exc}')
                        await asyncio.sleep(1)
        await asyncio.sleep(60 * 60)


async def check_accesses():
    await rights_control.check_all()

async def update_all_data_in_db_run(tasks):
    wb_accesses = super_cabinet_manager.get_accesses_for_wb_cabinets()
    logger.debug('Получен генератор к кабинетам для обновления даты')
    async for wb_access in wb_accesses:
        logger.debug('Получен кабинет для обновления данных')
        if wb_access.wb_cabinet.id not in tasks:
            try:
                shop_data_updater = ShopDataUpdater(wb_access)
            except ApiForbiddenError:
                logger.debug(f'Нет нужных прав у токена')
                await asyncio.sleep(0)
                continue

            async def task_with_delay():
                await shop_data_updater.update_all_data()
                await asyncio.sleep(15*60)
            task = asyncio.create_task(task_with_delay())
            logger.debug(f'Задача обновления данных для кабинета {wb_access.wb_cabinet.shop_id} создана')
            tasks[wb_access.wb_cabinet.id] = task
        else:
            if tasks[wb_access.wb_cabinet.id].done():
                logger.debug(f'Задача обновления данных для кабинета {wb_access.wb_cabinet.shop_id} завершена')
                if tasks[wb_access.wb_cabinet.id].exception():
                    logger.error(
                        f'Ошибка обновления данных для Shop id {wb_access.wb_cabinet.shop_id}: {tasks[wb_access.wb_cabinet.id].exception()}, '
                        f'{tasks[wb_access.wb_cabinet.id].exception()}')
                else:
                    async with sm(read_only=False) as session:
                        wb_cabinet = wb_access.wb_cabinet
                        stmt = select(WBCabinet).where(WBCabinet.id == wb_cabinet.id)
                        result = await session.execute(stmt)
                        wb_cabinet = result.scalar()
                        wb_cabinet.last_update_all_data = datetime.datetime.now()
                        await session.commit()
                    logger.debug('Задача обновления успешно выполнена')
                del tasks[wb_access.wb_cabinet.id]
        await asyncio.sleep(15*60)




async def insert_or_update_keywords(client, keyword_stats, adv_setting):
        # Подготовка данных для вставки
        new_version = int(datetime.datetime.now().timestamp())
        data_to_insert = []
        for kw in keyword_stats:
            date_time = datetime.datetime.combine(kw.date, datetime.datetime.min.time())#просто добавляем время к дате
            data_to_insert.append([kw.text,
                                   date_time,
                                   adv_setting.adv_id,
                                   kw.views,
                                   kw.clicks,
                                   kw.spend,
                                   new_version])

        await client.insert(table="default_db.advkeyword",
                            data=data_to_insert,
                                column_names=["text",
                                              "date",
                                              "adv_id",
                                              "views",
                                              "clicks",
                                              "spend",
                                              "version"] )


async def update_keywords_stat_in_click_house(client, keyword_stats: List[KeywordStat],
                                              adv_setting: AdvSetting):
    await insert_or_update_keywords(client, keyword_stats, adv_setting)


async def get_existing_keyword_settings(adv_setting_id) -> set[str]:
    async with sm() as session:
        stmt = select(KeywordSetting).where(
            KeywordSetting.adv_setting_id == adv_setting_id
        )
        result = await session.execute(stmt)
        existing_keyword_settings: list[KeywordSetting] = result.scalars().all()
    return {ks.text for ks in existing_keyword_settings}


async def update_predict_ctr():
    while True:
        try:
            logger.debug('Начинаю прогноз CTR')
            predictor = Predictor()
            await predictor.predict_ctr_for_keywords()
        except Exception as exc:
            logger.error(f'Ошибка предсказания CTR {exc}')
        await asyncio.sleep(0)

async def update_all_keyword_data(access,
                                  adv_setting,
                                  wb_cabinet: WBCabinet,
                                  keywords: list[KeywordStat] = None,
                                  wb_api: WBApi = None):

    try:
        if not wb_api:
             wb_api = WBApi(access)
        async with get_clickhouse_client() as client:
            await common_keyword_stat_update(client, adv_setting, wb_api)
    except ApiForbiddenError:
        logger.error(f'Нет доступов для обновления данных магазина: {access.wb_cabinet.shop_id}')
        return
    except Exception as exc:
        logger.error('Ошибка обновления статистики ключевых слов', exc_info=True)
        raise exc
    try:
        data_setter = DataSetter(access)
        await data_setter.update_minus_keywords_in_adv(adv_setting,
                                                       wb_cabinet,
                                                       keywords)
    except Exception as exc:
        logger.error('Ошибка установки активности фраз', exc_info=True)
        raise exc
    return




async def update_all_keywords_on_wb():
    update_tasks: dict[int, asyncio.Task] = {}
    while True:
        async with sm() as session:
            stmt = select(AdvSetting) \
                .where(AdvSetting.bot_active == True)
            result = await session.execute(stmt)
            adv_settings: list[AdvSetting] = result.scalars().all()
            for adv_setting in adv_settings:
                if adv_setting.id not in update_tasks:
                    wb_cabinet_id = adv_setting.wb_cabinet_id
                    access: WBCabinetAccess = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
                    if not access:
                        logger.error(f'Нет доступа к кабинету {wb_cabinet_id}')
                        continue
                    task = asyncio.create_task(update_all_keyword_data(access,
                                                                       adv_setting,
                                                                       wb_cabinet=access.wb_cabinet))
                    update_tasks[adv_setting.id] = task
                else:
                    if update_tasks[adv_setting.id].done():
                        if update_tasks[adv_setting.id].exception():
                            logger.error(f'Ошибка обновления ключей  для shop_id: {access.wb_cabinet.shop_id} '
                                         f'Кампания: {adv_setting.adv_id} '
                                         f' {update_tasks[adv_setting.id].exception()}',
                                         exc_info=True)
                        del update_tasks[adv_setting.id]
                await asyncio.sleep(0)


#
#
# async def update_keyword_stat(access: WBCabinetAccess,
#                               adv_update_tasks: dict[int, asyncio.Task]):
#     wb_api = WBApi(access)
#     wb_cabinet = access.wb_cabinet
#     logger.debug(f"Начало обновления статистики для кабинета {wb_cabinet.id}")
#
#     async with sm() as session:
#         stmt = select(AdvSetting).where(and_(
#             AdvSetting.wb_cabinet_id == wb_cabinet.id,
#             AdvSetting.type == 8,
#             AdvSetting.bot_active == True,
#             AdvSetting.active_status == 'started'
#
#         )).order_by(AdvSetting.last_update.desc())
#         result = (await session.execute(stmt)).unique()
#         adv_settings = result.scalars().all()
#     async with get_clickhouse_client() as client:
#         for adv_setting in adv_settings:
#             adv_id = adv_setting.adv_id
#             if adv_id not in adv_update_tasks:
#                 task = asyncio.create_task(keyword_stat_updater(client, adv_setting, wb_api))
#                 adv_update_tasks[adv_id] = task
#             else:
#                 if adv_update_tasks[adv_id].done():
#                     logger.info(
#                         f'Задача обновления статистики ключей завершена для adv_id '
#                         f'{adv_id}'
#                     )
#                     if adv_update_tasks[adv_id].exception():
#                         logger.error(
#                             f'Ошибка обновления статистики ключей: '
#                             f'{adv_update_tasks[adv_id].exception()},'
#                             f' для кабинета {access.wb_cabinet.shop_id}', exc_info=True
#                         )
#
#                     del adv_update_tasks[adv_id]
#                     logger.info(f'Статистика ключевых слов для {adv_id} обновлена')
#                     logger.debug(f'Установка set для need_update_model')
#                     logger.debug(f"Обновление статистики завершено")
#             await asyncio.sleep(0)
#     return



async def update_clusters_for_adv(adv: AdvSetting, wb_api: WBApi):
    try:
        clusters = await wb_api.advert.get_clusters_for_adv(adv)
        clusters = clusters['clusters']
        if not clusters:
            return
        for cluster in clusters:
            cluster_name = cluster['cluster'].strip().lower()
            keywords = cluster['keywords']
            for keyword_text in keywords:
                keyword_text = keyword_text.strip().lower()
                await redis_manager.set_keyword_cluster(keyword_text, cluster_name)
    except Exception as e:
        logger.debug(f'Error getting clusters for adv {adv.id}: {e}', exc_info=True)
        return


async def update_clusters_for_cabinet(access: WBCabinetAccess, tasks):
    try:
        wb_api = WBApi(access)
    except ApiForbiddenError:
        logger.error('Доступ запрещен')
        return
    async with sm() as session:
        query = select(AdvSetting).where(AdvSetting.wb_cabinet_id == access.wb_cabinet.id)
        adv_settings = await session.execute(query)
        adv_settings = adv_settings.scalars().all()
    for adv in adv_settings:
        if adv.id not in tasks:
            task = asyncio.create_task(update_clusters_for_adv(adv, wb_api))
            tasks[adv.id] = task
        else:
            if tasks[adv.id].done():
                logger.debug(f'Задача обновления кластеров завершена для РК {adv.name}')
                if tasks[adv.id].exception():
                    logger.error(f'Ошибка обновления кластеров: {tasks[adv.id].exception()}')
                del tasks[adv.id]
        await asyncio.sleep(0)



# async def keyword_stat_updater(client, adv_setting: AdvSetting, wb_api):
#     try:
#         await keyword_stat_updater(client, adv_setting, wb_api)
#     except Exception as exc:
#         logger.error(f'Ошибка обновления статистики ключей для кампании: {adv_setting.name}, '
#                           f'adv_id: {adv_setting.adv_id}, '
#                           f'shop_id: {wb_api.wb_access.wb_cabinet.shop_id}, {exc}', exc_info=True)



async def common_keyword_stat_update(client, adv_setting: AdvSetting, wb_api):
    adv_id = adv_setting.adv_id
    try:
        keywords_from_auto: list[KeywordStat] = await wb_api.advert.get_keywords_stat(adv_id)
    except ApiForbiddenError as exc:
        raise exc
    except Exception as exc:
        keywords_from_auto = []
        logger.error(f'Ошибка получения статистики по ключевым словам для кампании: {adv_setting.name}, '
                     f'shop_id: {wb_api.wb_access.wb_cabinet.shop_id}, {exc}', exc_info=True)
    try:
        if not adv_setting.search_adv_id:
            keywords_from_search_adv = []
        else:
             keywords_from_search_adv = await wb_api.advert.get_keywords_stat(adv_setting.search_adv_id)
    except Exception as exc:
        keywords_from_search_adv = []
        logger.error(f'Ошибка получения статистики по ключевым словам для {adv_setting.name}, {exc}')

    if not keywords_from_auto and not keywords_from_search_adv:
        logger.debug(f'Пустой список ключевых слов для {adv_setting.adv_id}')
        return

    text_to_keyword_from_auto = {kw.text + ':' + str(kw.date): kw for kw in keywords_from_auto}
    for kw in keywords_from_search_adv:
        key = kw.text + ':' + str(kw.date)
        if key not in text_to_keyword_from_auto:
            text_to_keyword_from_auto[key] = kw
        else:
            text_to_keyword_from_auto[key].views += kw.views
            text_to_keyword_from_auto[key].clicks += kw.clicks
            text_to_keyword_from_auto[key].spend += kw.spend
    full_stat  = list(text_to_keyword_from_auto.values())

    keywords = full_stat

    logger.debug(f'Получено {len(keywords)} ключевых слов для {adv_setting.name}')
    texts_for_adv_setting = {keyword.text for keyword in keywords}
    clusters = set()
    for text in texts_for_adv_setting:
        try:
            cluster_name, _ = await redis_manager.get_cluster_and_preset(text)
        except:
            logger.error('Не удалось получить кластер')
            cluster_name = None

        if cluster_name:
           clusters.add(cluster_name)

    texts_for_adv_setting.update(clusters)
    existing_keyword_settings = await get_existing_keyword_settings(adv_setting.id)
    new_keywords: set[str] = texts_for_adv_setting - existing_keyword_settings

    # Преобразование ключевых слов в объекты KeywordSetting
    keyword_settings = [KeywordSetting(text=keyword, adv_setting_id=adv_setting.id) for keyword in new_keywords]
    try:
        async with sm(read_only=False) as session:
            # Обработка данных порциями
            for keyword in keyword_settings:
                check_by_black_list_template = await data_manager.check_by_black_list_template(keyword.text, adv_setting.id)
                if check_by_black_list_template:
                    keyword.hard_status = 0
                session.add(keyword)
            await session.commit()
    except Exception as exc:
        logger.error(f'Ошибка добавления ключевых слов в базу данных: {exc}', exc_info=True)
        raise exc

    await update_keywords_stat_in_click_house(client, keywords, adv_setting)

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

class Manager(AbcManager):
    # async def insert_keyword_stats(self, client, keyword_stats, adv_setting):
    #     try:
    #         # Генерация новой версии на основе текущего времени
    #         new_version = int(datetime.datetime.now().timestamp())
    #
    #         data_to_insert = [
    #             [kw.text, kw.date, adv_setting.adv_id, kw.views, kw.clicks, kw.spend, new_version]
    #             for kw in keyword_stats
    #         ]
    #
    #         await self._insert_keyword_stats(client, data_to_insert)
    #     except Exception as e:
    #         logger.error(f"Error inserting data into ClickHouse: {e}")
    #         raise
    #



    #
    #
    # def save_full_predict(self):
    #     # Загрузка данных с помощью Dask
    #     nmids_vectors = dd.read_csv(self.nmids_vectors_path)
    #     keyword_vectors = dd.read_csv(self.keywords_vectors_path)
    #     # nmid_offer_id_df = dd.read_csv(self.nmid_offer_id_shop_name_df_path)
    #
    #     # Получение уникальных значений
    #     nmids = nmids_vectors['nmid'].unique().compute()
    #     keywords = keyword_vectors['keyword'].unique().compute()
    #
    #     # Загрузка модели
    #     model = joblib.load(self.model_path)
    #
    #     # Инициализация пустого DataFrame для результатов
    #     final_result = pd.DataFrame()
    #
    #     # Прямая генерация и обработка комбинаций
    #     batch_size = 10000  # Определение размера партии для обработки
    #     total_combinations = len(nmids) * len(keywords)
    #     num_batches = (total_combinations + batch_size - 1) // batch_size  # Вычисление необходимого количества партий
    #
    #     for i in range(num_batches):
    #         # Генерация части комбинаций
    #         start_idx = i * batch_size
    #         end_idx = min(start_idx + batch_size, total_combinations)
    #         batch_combs = list(product(nmids, keywords))[start_idx:end_idx]
    #
    #         # Преобразование в DataFrame
    #         df_batch = pd.DataFrame(batch_combs, columns=['nmid', 'keyword'])
    #         ddf_batch = dd.from_pandas(df_batch, npartitions=10)
    #
    #         # Объединение данных с помощью Dask
    #         df_with_feature = ddf_batch.merge(nmids_vectors, how='left', on=['nmid'])
    #         df_with_feature = df_with_feature.merge(keyword_vectors, how='left', on=['keyword']).dropna()
    #
    #         # Выбор признаков для модели и выполнение предсказаний
    #         X_batch = df_with_feature.drop(['nmid', 'keyword'],
    #                                        axis=1).compute()  # Перевод в pandas DataFrame для модели
    #         y_batch = model.predict(X_batch)
    #
    #         # Сохранение результатов
    #         result_batch = pd.concat([df_batch.reset_index(drop=True), pd.Series(y_batch, name='prediction')], axis=1)
    #         final_result = pd.concat([final_result, result_batch], ignore_index=True)
    #
    #
    #     # Вывод итогового DataFrame
    #     print(final_result)

    @staticmethod
    def __load_ml_model(model_path,):
        return joblib.load(model_path)



    def __save_model( model, model_path):
        joblib.dump(model, model_path)


    def __get_keyword_stat(self):
        kw_df = pd.read_csv(self.keyword_stat_df_path)
        return kw_df



    async def get_nearest_surrogate_phrases(self, phrases: set[str]):
        if self._phrase_index is None:
            index = await asyncio.to_thread(self._get_phrase_index)
            self._phrase_index = index
        else:
            index = self._phrase_index

        surrogate_phrase_dict = {}
        loop = asyncio.get_event_loop()
        for phrase in phrases:
            word2vec_vec = await self._word2vec.average_vector_from_sentence(phrase)
            if word2vec_vec is None:
                continue

            prhase_node_id = int(index.get_near_object_id(word2vec_vec))
            surrogate_keyword = await loop.run_in_executor(None,
                                                self._gds.get_keyword_phrase_vector_by_id,
                                                prhase_node_id)

            surrogate_phrase_dict[phrase] = surrogate_keyword
        return surrogate_phrase_dict



    async def __find_most_similar(self, phrase, index):
        vector = await self._word2vec.average_vector_from_sentence(phrase)
        vector = np.array(vector).reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(vector)
        distances, indices = index.search(vector, 1)  # Ищем наиболее похожий вектор
        return indices[0, 0]

    def _get_phrase_index(self):
       index = self._faiss_manager.get_keyword_phrases_index()
       return index




    @staticmethod
    async def update_min_ctr_in_global_wb_category_settings():
        parent_categories_to_subcategories_name_list = await data_manager.get_parent_id_categories_subcategories_name_list()
        category_name_to_parent_id = {}
        for parent_id, subcategories in parent_categories_to_subcategories_name_list.items():
            for subcategory in subcategories:
                category_name_to_parent_id[subcategory] = parent_id
        logger.debug('Родительские категории для расчета  min_ctr получены')
        wb_category_to_keywordstat_list = await data_manager.get_wb_category_to_keywordstat_list()
        parent_category_to_keywordstat_list = {}
        for wb_category_name, keywordstat_list in wb_category_to_keywordstat_list.items():
            parentId = category_name_to_parent_id[wb_category_name]
            if parentId not in parent_category_to_keywordstat_list:
                parent_category_to_keywordstat_list[parentId] = []
            parent_category_to_keywordstat_list[parentId].extend(keywordstat_list)
        global_keywordstats_list = []
        for keywordstat_list in parent_category_to_keywordstat_list.values():
            global_keywordstats_list.extend(keywordstat_list)
        global_keywordstats_list = [keywordstat for keywordstat in global_keywordstats_list if keywordstat.ctr > 0]
        final_wb_category_name_to_min_ctr = {}
        percentile = 5
        for wb_category_name, keywordstat_list in wb_category_to_keywordstat_list.items():
            ctrs = np.array([keywordstat.ctr for keywordstat in keywordstat_list if keywordstat.ctr > 0])
            if ctrs.size > 0:
                min_ctr = np.percentile(ctrs, percentile)
                final_wb_category_name_to_min_ctr[wb_category_name] = min_ctr
            else:
                parentId = category_name_to_parent_id[wb_category_name]
                keywordstats = parent_category_to_keywordstat_list[parentId]
                ctrs = np.array([keywordstat.ctr for keywordstat in keywordstats if keywordstat.ctr > 0])
                if ctrs.size > 0:
                    min_ctr = np.percentile(ctrs, percentile)
                    final_wb_category_name_to_min_ctr[wb_category_name] = min_ctr
                else:
                    ctrs = np.array([kw.ctr for kw in global_keywordstats_list])
                    if ctrs.size > 0:
                        min_ctr = np.percentile(ctrs, percentile)
                        final_wb_category_name_to_min_ctr[wb_category_name] = min_ctr
                    else:
                        final_wb_category_name_to_min_ctr[wb_category_name] = 0  # И тут
        async with sm(read_only=False) as session:
            for wb_category_name, min_ctr in final_wb_category_name_to_min_ctr.items():
                # if message_counter.check_last_time():
                #      await admin_sender.send_message_to_admin(f'Минимальный CTR для категории {wb_category_name} установлен в {min_ctr}')


                stmt = select(GlobalCategorySetting) \
                    .where(GlobalCategorySetting.category_name == wb_category_name)
                category_setting = await session.execute(stmt)
                category_setting = category_setting.scalar()
                if not category_setting:
                    category_setting = GlobalCategorySetting(category_name=wb_category_name, min_ctr=min_ctr)
                    session.add(category_setting)
                else:
                    category_setting.min_ctr = min_ctr
                await session.execute(stmt)
            await session.commit()
            message_counter.add_send()



    async def clear_expired_data(self):
        async with sm(read_only=False) as session:
            expired_cabinets: list[WBCabinet] = await data_manager.get_expired_cabinets(session)
            for wb_cabinet in expired_cabinets:
                adv_settings: list[AdvSetting] = wb_cabinet.adv_settings
                for adv_setting in adv_settings:
                    await session.delete(adv_setting)
                    await session.commit()
        nmids = list(set(await data_manager.get_needs_nmids()))
        await data_manager.clear_cards_in_db(nmids=nmids)
        await self._gds.clear_cards_in_neo4j(need_nmids=nmids)
        keywords = list(set(await data_manager.get_all_keywords()))
        await self._gds.clear_keywords_in_neo4j(need_keywords=keywords)
        await self._gds.clear_dead_nodes()
        await asyncio.sleep(60 * 60)


