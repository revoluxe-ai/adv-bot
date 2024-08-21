import logging
from typing import List
from itertools import product
import dask.dataframe as dd
import faiss
import joblib
import numpy as np
from sqlalchemy import not_
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
from ...client_bot import const
from ...utils import redis_manager
from  app.modules.wb_keywords_parser import parser
from app.utils.click_house.client import get_clickhouse_client




logger = logging.getLogger(__name__)

gds = DataScience()

sm = get_async_session_maker

keywords_hashs_in_neo = set()


async def process_payment_for_auto_bidder():
    current_date = datetime.datetime.now().date()
    async with sm() as session:
        stmt = select(AdvSetting).options(
            joinedload(AdvSetting.payments),
            selectinload(AdvSetting.wb_cabinet)
        ).filter(
            and_(
                AdvSetting.bidder_active == True,
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
    async with sm() as session:
        stmt = select(AdvSetting).options(
            joinedload(AdvSetting.payments),
            selectinload(AdvSetting.wb_cabinet)
        ).filter(
            and_(
                AdvSetting.parsing_active == True,
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
    async with sm() as session:
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
        async with sm() as session:
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
                logger.error(f'Нет нужных прав у токена')
                continue
            task = asyncio.create_task(shop_data_updater.update_all_data())
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
                    async with sm() as session:
                        wb_cabinet = wb_access.wb_cabinet
                        stmt = select(WBCabinet).where(WBCabinet.id == wb_cabinet.id)
                        result = await session.execute(stmt)
                        wb_cabinet = result.scalar()
                        wb_cabinet.last_update_all_data = datetime.datetime.now()
                        await session.commit()
                    logger.debug('Задача обновления успешно выполнена')
                del tasks[wb_access.wb_cabinet.id]
        await asyncio.sleep(0)




async def insert_or_update_keywords(client, keyword_stats, adv_setting):
    try:
        # Подготовка данных для вставки
        new_version = int(datetime.datetime.now().timestamp())
        data_to_insert = []
        for kw in keyword_stats:
            date_time = datetime.datetime.combine(kw.date, datetime.datetime.min.time())
            data_to_insert.append([kw.text,
                                   date_time,
                                   adv_setting.adv_id,
                                   kw.views, kw.clicks,
                                   kw.spend,
                                   new_version])


        # Удаление существующих записей

        # Вставка новых данных
        await client.insert(table="default_db.advkeyword"
                            , data=data_to_insert,
                            column_names=["text", "date", "adv_id", "views", "clicks", "spend", "version"] )

    except Exception as e:
        logger.error(f"Error handling data in ClickHouse: {e}")
        raise







async def update_keywords_stat_in_click_house(keyword_stats: List[KeywordStat],
                                              adv_setting: AdvSetting):
    client = await get_clickhouse_client()
    try:
        await insert_or_update_keywords(client, keyword_stats, adv_setting)
    except Exception as e:
        logger.error(f"Error inserting data into ClickHouse: {e}")
        raise
    finally:
        client.close()


async def get_existing_keyword_settings(adv_setting_id) -> set[str]:
    async with sm() as session:
        stmt = select(KeywordSetting).where(
            KeywordSetting.adv_setting_id == adv_setting_id
        )
        result = await session.execute(stmt)
        existing_keyword_settings = result.scalars().all()
    return {ks.text for ks in existing_keyword_settings}


async def update_predict_ctr():
    predictor = Predictor()
    while True:
        try:
            await predictor.predict_ctr_for_keywords()
        except Exception as exc:
            logger.error(f'Ошибка предсказания CTR {exc}')
        await asyncio.sleep(0)



async def update_keywords_in_advs():
    update_tasks: dict[int, asyncio.Task] = {}
    while True:
        accesses  = super_cabinet_manager.get_accesses_for_wb_cabinets()
        logger.debug('Получен генератор доступов к кабинетам для обновления минус-ключей в РК')
        async for access in accesses:
            logger.debug('Получен кабинет для обновления минус-ключей в РК')
            wb_cabinet_id = access.wb_cabinet.id
            if wb_cabinet_id  not in update_tasks:
                try:
                    data_setter = DataSetter(access)
                except ApiForbiddenError:
                    logger.error(f'Нет нужных прав у токена')
                    continue
                logger.debug(access.wb_cabinet.id)
                async with sm() as session:
                    stmt = select(AdvSetting) \
                        .where(and_(AdvSetting.bot_active == True,
                                    AdvSetting.wb_cabinet_id == wb_cabinet_id))
                    result = await session.execute(stmt)
                    adv_settings: list[AdvSetting] = result.scalars().all()
                if adv_settings:
                    logger.debug(f'Запуск задачи обновления минус-ключей для кабинета {wb_cabinet_id}')
                    task = asyncio.create_task(data_setter.update_minus_keywords(adv_settings))
                    update_tasks[wb_cabinet_id] = task
            else:
                if update_tasks[wb_cabinet_id].done():
                    if update_tasks[wb_cabinet_id].exception():
                        logger.error(f'Ошибка обновления ключей: {update_tasks[wb_cabinet_id].exception()}',
                                     exc_info=True)
                    del update_tasks[wb_cabinet_id]
        await asyncio.sleep(0)



async def update_keyword_stat(access: WBCabinetAccess,
                              adv_update_tasks: dict[int, asyncio.Task]):
    wb_api = WBApi(access)
    wb_cabinet = access.wb_cabinet
    logger.debug(f"Начало обновления статистики для кабинета {wb_cabinet.id}")

    async with sm() as session:
        stmt = select(AdvSetting).where(and_(
            AdvSetting.wb_cabinet_id == wb_cabinet.id,
            AdvSetting.type == 8,
        )).order_by(AdvSetting.last_update.desc())
        result = (await session.execute(stmt)).unique()
        adv_settings = result.scalars().all()
    for adv_setting in adv_settings:
        if adv_setting not in adv_update_tasks:
            task = asyncio.create_task(keyword_stat_updater(adv_setting.id, wb_api))
            adv_update_tasks[adv_setting.id] = task
        else:
            if adv_update_tasks[adv_setting.id].done():
                logger.info(
                    f'Задача обновления статистики ключей завершена для кабинета '
                    f'{adv_setting.name}'
                )
                if adv_update_tasks[adv_setting.id].exception():
                    logger.error(
                        f'Ошибка обновления статистики ключей: '
                        f'{adv_update_tasks[adv_setting.id].exception()},'
                        f' для кабинета {adv_setting.name}'
                    )

                del adv_update_tasks[adv_setting.id]
                logger.info(f'Статистика ключевых слов для {adv_setting.name} обновлена')
                logger.debug(f'Установка set для need_update_model')
                logger.debug(f"Обновление статистики завершено")
        await asyncio.sleep(0)
    return


async def keyword_stat_updater(adv_setting_id, wb_api):
    async with sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
        adv_setting = await session.execute(stmt)
        adv_setting = adv_setting.scalar()
    try:
        keywords: list[KeywordStat] = await wb_api.advert.get_keywords_stat(adv_setting)
    except Exception as exc:
        logger.error(
            f'Ошибка получения статистики по ключевым словам для {adv_setting.name}, {exc}')
        return
    if not keywords:
        logger.debug(f'Для {adv_setting.name} не получены ключевые слова')
        return
    logger.debug(f'Получено {len(keywords)} ключевых слов для {adv_setting.name}')
    texts_for_adv_setting = {keyword.text for keyword in keywords}
    existing_keyword_settings = await get_existing_keyword_settings(adv_setting.id)
    new_keywords: set[str] = texts_for_adv_setting - existing_keyword_settings
    async with sm() as session:
        for keyword in new_keywords:
            keyword_setting = KeywordSetting(
                text=keyword,
                adv_setting_id=adv_setting.id,
            )
            session.add(keyword_setting)

        await session.commit()
    await update_keywords_stat_in_click_house(keywords, adv_setting)
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





    def save_full_predict(self):
        # Загрузка данных с помощью Dask
        nmids_vectors = dd.read_csv(self.nmids_vectors_path)
        keyword_vectors = dd.read_csv(self.keywords_vectors_path)
        # nmid_offer_id_df = dd.read_csv(self.nmid_offer_id_shop_name_df_path)

        # Получение уникальных значений
        nmids = nmids_vectors['nmid'].unique().compute()
        keywords = keyword_vectors['keyword'].unique().compute()

        # Загрузка модели
        model = joblib.load(self.model_path)

        # Инициализация пустого DataFrame для результатов
        final_result = pd.DataFrame()

        # Прямая генерация и обработка комбинаций
        batch_size = 10000  # Определение размера партии для обработки
        total_combinations = len(nmids) * len(keywords)
        num_batches = (total_combinations + batch_size - 1) // batch_size  # Вычисление необходимого количества партий

        for i in range(num_batches):
            # Генерация части комбинаций
            start_idx = i * batch_size
            end_idx = min(start_idx + batch_size, total_combinations)
            batch_combs = list(product(nmids, keywords))[start_idx:end_idx]

            # Преобразование в DataFrame
            df_batch = pd.DataFrame(batch_combs, columns=['nmid', 'keyword'])
            ddf_batch = dd.from_pandas(df_batch, npartitions=10)

            # Объединение данных с помощью Dask
            df_with_feature = ddf_batch.merge(nmids_vectors, how='left', on=['nmid'])
            df_with_feature = df_with_feature.merge(keyword_vectors, how='left', on=['keyword']).dropna()

            # Выбор признаков для модели и выполнение предсказаний
            X_batch = df_with_feature.drop(['nmid', 'keyword'],
                                           axis=1).compute()  # Перевод в pandas DataFrame для модели
            y_batch = model.predict(X_batch)

            # Сохранение результатов
            result_batch = pd.concat([df_batch.reset_index(drop=True), pd.Series(y_batch, name='prediction')], axis=1)
            final_result = pd.concat([final_result, result_batch], ignore_index=True)


        # Вывод итогового DataFrame
        print(final_result)

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
        async with sm() as session:
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
        async with sm() as session:
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
        await asyncio.sleep(60*60)


