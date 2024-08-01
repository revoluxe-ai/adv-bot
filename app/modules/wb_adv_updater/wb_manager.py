import logging
import re
import typing
from typing import List

import aiohttp
from io import BytesIO
from itertools import product
import dask.dataframe as dd
import faiss
import joblib
import numpy as np
from PIL import Image as PilImage
from sqlalchemy import and_, not_
from sqlalchemy.orm.base import _T_co

from app.client_bot.bot import bot
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_adv_updater.models import AdvPayment
from app.utils.faiss_manager.faiss_index_manager import FaissManager
from app.utils.text_master.Transformers import Word2Vec
from .ABC_manager import AbcManager
from .data_manager import DataGetter, DataSetter
from .graph_vector_updater import GraphUpdater
from app.modules.common_slaves.wildberries.data_classes.namedtuples import KeywordStatForNeo, KeywordPhrase
from ..common_slaves.wildberries import super_cabinet_manager
from .ML import Fitter
from app.my_types import KeywordStat
from app.utils.NeoDataScience.driver import DataScience
from app.modules.common_slaves.wildberries.models import WBCard, WBCabinet

from app.utils.image_master.image_master2 import ImageMaster
import pymystem3
from app.utils.image_master import image_tools
import asyncio
from app.admin_bot.sender import messages
import pandas as pd
from sqlalchemy import and_
from sqlalchemy.orm import joinedload, selectinload, InstrumentedAttribute
from sqlalchemy.future import select
from .ML import Predictor
import datetime
from app.modules.common_slaves.wildberries.models import (WBUserCabinet,
                                                          AdvSetting,
                                                          AdvKeyword,
                                                          KeywordSetting)
from app.modules.wb_adv_updater.models import GlobalCategorySetting
from app.utils.db.session_maker import get_async_session_maker
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from ..common_slaves.wildberries.exceptions import ApiForbiddenError
from ..common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from .shops_manager import rights_control
from ...client_bot import const
from ...utils import redis_manager
from ...utils.redis_manager import RedisEvent
from  app.modules.wb_keywords_parser import parser



predictor = Predictor()


logger = logging.getLogger(__name__)


sm = get_async_session_maker

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
    _fitter = Fitter()
    _data_getter = DataGetter()
    graph_updater = GraphUpdater()
    # _shop_manager = ShopManager()
    _word2vec = Word2Vec()
    _faiss_manager = FaissManager()
    _lock = asyncio.Lock()
    _predictor = Predictor()

    def __init__(self):
        self._image_master = ImageMaster()
        self._phrase_index = None
        self._gds = DataScience()
        self._word2vec = Word2Vec()
        self._aiosm = get_async_session_maker
        self._pymystem = pymystem3.Mystem()
        self._image_tools = image_tools

    async def update_keyword_stat(self, access: WBCabinetAccess,
                                  need_update_model: asyncio.Event,
                                  adv_update_tasks: dict[int, asyncio.Task],
                                  semaphore: asyncio.Semaphore):
        wb_api = WBApi(access)
        wb_cabinet = access.wb_cabinet
        logger.debug(f"Начало обновления статистики для кабинета {wb_cabinet.id}")

        async with sm(semaphore) as session:
            stmt = select(AdvSetting).where(and_(
                AdvSetting.wb_cabinet_id == wb_cabinet.id,
                AdvSetting.type == 8,
                AdvSetting.bot_active == True,

            )).order_by(AdvSetting.last_update.desc())
            result = (await session.execute(stmt)).unique()
            adv_settings = result.scalars().all()
        for adv_setting in adv_settings:
            if adv_setting not in adv_update_tasks:
                task = asyncio.create_task(self.keyword_stat_updater(adv_setting.id, wb_api, semaphore))
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
                    need_update_model.set()
                    logger.debug(f"Обновление статистики завершено")
            await asyncio.sleep(0)
        return

    @staticmethod
    async def update_keyword_stat_in_db(keyword_stat: KeywordStat,
                                        adv_setting: AdvSetting,
                                        session):
        adv_setting_original_id = adv_setting.id
        # Проверяем наличие записи в KeywordSetting
        stmt = select(KeywordSetting).filter(
            KeywordSetting.text == keyword_stat.text,
            KeywordSetting.adv_setting_id == adv_setting_original_id
        )
        result = await session.execute(stmt)
        keyword_setting = result.scalar()

        # Если запись отсутствует, создаем новую
        if not keyword_setting:
            keyword_setting = KeywordSetting(
                text=keyword_stat.text,
                adv_setting_id=adv_setting_original_id
            )
            session.add(keyword_setting)
            try:
                await session.commit()  # Коммит для получения ID новой записи
                await session.refresh(keyword_setting)  # Обновляем объект, чтобы получить ID
            except Exception as e:
                await session.rollback()
                raise e  # Обработка исключения

        # Проверяем наличие записи в AdvKeyword
        stmt = select(AdvKeyword).options(selectinload(AdvKeyword.keyword_setting)).filter(
            AdvKeyword.text == keyword_stat.text,
            AdvKeyword.date == keyword_stat.date,
            AdvKeyword.adv_setting_id == adv_setting_original_id
        ).order_by(AdvKeyword.date.desc())
        result = await session.execute(stmt)
        keyword_db = result.scalar()

        # Если запись отсутствует, создаем новую
        if not keyword_db:
            keyword_db = AdvKeyword(
                text=keyword_stat.text,
                date=keyword_stat.date,
                adv_setting_id=adv_setting_original_id,
                keyword_setting_id=keyword_setting.id,  # Здесь мы устанавливаем значение keyword_setting_id
                views=keyword_stat.views,
                clicks=keyword_stat.clicks,
                spend=keyword_stat.spend
            )
            session.add(keyword_db)
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e  # Обработка исключения
        else:
            # Если запись существует, проверяем и обновляем данные
            updated = False
            if not keyword_db.keyword_setting:
                keyword_db.keyword_setting = keyword_setting
                updated = True
            if any([keyword_db.views != keyword_stat.views, keyword_db.clicks != keyword_stat.clicks]):
                keyword_db.views = keyword_stat.views
                keyword_db.clicks = keyword_stat.clicks
                keyword_db.spend = keyword_stat.spend
                updated = True

            if updated:
                try:
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    raise e  # Обработка исключения
        return

    async def keyword_stat_updater(self, adv_setting_id, wb_api, semaphore):
        async with sm(semaphore) as session:
            stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
            adv_setting = await session.execute(stmt)
            adv_setting = adv_setting.scalar()
        try:
            keywords: list[KeywordStat] = await wb_api.advert.get_keywords_stat(adv_setting)
        except Exception as exc:
            logger.error(
                f'Ошибка получения статистики по ключевым словам для {adv_setting.name}, {exc}')
            return
        logger.info(f'Получено {len(keywords)} ключевых слов для {adv_setting.name}')
        async with sm(semaphore) as session:
            for keyword in keywords:
                try:
                    await self.update_keyword_stat_in_db(keyword, adv_setting,  session)
                    logger.debug(f'Статистика для ключевого слова {keyword.text} обновлена')
                except Exception as exc:
                    logger.error(
                        f'Ошибка при обновлении статистики ключевых слов для {adv_setting.name}, {exc}',
                        exc_info=True
                    )
                await asyncio.sleep(0)
        async with sm(semaphore) as session:
            stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
            adv_setting = await session.execute(stmt)
            adv_setting = adv_setting.scalar()
            adv_setting.last_update = datetime.datetime.now()
            await session.commit()
        return


    async def graph_vector_update(self) -> None:
        length = 2**4
        await self.graph_updater.update_graph_run(length)
        await asyncio.sleep(1)
        return


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

    @staticmethod
    async def update_keywords_in_advs(semaphore) -> list[typing.Awaitable]:
        update_tasks: dict[int, asyncio.Task] = {}
        while True:
            accesses  = super_cabinet_manager.get_accesses_for_wb_cabinets(semaphore)
            async for access in accesses:
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
                        task = asyncio.create_task(data_setter.update_minus_keywords(adv_settings))
                        update_tasks[wb_cabinet_id] = task
                else:
                    if update_tasks[wb_cabinet_id].done():
                        if update_tasks[wb_cabinet_id].exception():
                            logger.error(f'Ошибка обновления ключей: {update_tasks[wb_cabinet_id].exception()}',
                                         exc_info=True)
                        del update_tasks[wb_cabinet_id]
            await asyncio.sleep(0)




    async def update_model(self, update_model_on_new_features):
        logger.debug('Старт обучения и сохранения модели')
        await self.fit_and_save_model(update_model_on_new_features)
        logger.debug('Устанавливаю сет, разрешаю обновление ключей')


    def __save_model( model, model_path):
        joblib.dump(model, model_path)


    async def fit_and_save_model(self, update_model_on_new_features):
        await self._fitter.getGradientBoostingFullFitModel(update_model_on_new_features)

    async def update_vectors_exec_mode(self):
             try:
                 await self.graph_vector_update()
                 await self.graph_updater.get_nmids_and_keyword_featers_for_ml()
             except Exception as exc:
                    logger.error(f'Ошибка обновления векторов {exc}')

    def __get_keyword_stat(self):
        kw_df = pd.read_csv(self.keyword_stat_df_path)
        return kw_df



    async def update_wb_adv_phrase_in_db(self, need_update_model):
        """update_model_on_new_features.set()"""
        try:
            await self.update_wb_adv_phrase_in_db_bot_active()
        except Exception as exc:
            logger.error(f'Ошибка обновления фраз в neo4j {exc}')
        need_update_model.set()

    async def update_wb_adv_phrase_in_db_bot_active(self):
        async with sm() as session:
            stmt = select(KeywordSetting.text)\
            .join(AdvSetting)\
            .filter(and_(AdvSetting.active_status == 'started',
                            AdvSetting.bot_active == True))
            result = await session.execute(stmt)
            texts = result.unique().scalars().all()
        texts = [text for text in texts if text]
        new_texts = []
        for text in texts:
            text = text.replace('_', ' ')
            text = text.replace(',', '.')
            new_texts.append(text)
        texts = new_texts
        # keyword_phrases_in_neo = await self._gds.get_keyword_phrases()
        phrase_data_list = []
        added_to_base = set()
        for text in texts:
            if self._gds.check_phrase_in_neo(text):
                logger.debug(f'Фраза {text} уже есть в базе данных')
                await asyncio.sleep(0)
                continue
            if text in added_to_base:
                logger.debug(f'Фраза {text} уже добавлена в список')
                await asyncio.sleep(0)
                continue
            words = text.split()
            keywords = []
            for word in words:
                vector = await self._word2vec.average_vector_from_sentence(word)
                if vector is not None:
                    vector = list(vector)
                keywords.append(KeywordStatForNeo(text=word, vector=vector))
                await asyncio.sleep(0)

            phrase_data = KeywordPhrase(
                text=text,
                words=keywords,
                word2vec=await self._word2vec.average_vector_from_sentence(text)

            )
            phrase_data_list.append(phrase_data)
            added_to_base.add(text)

        batch = 100
        for i in range(0, len(phrase_data_list), batch):
            await self._gds.add_keyword_phrase(phrase_data_list[i:i+batch])
            await asyncio.sleep(0)

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

    async def update_cards_in_graph_for_shops(self):
        async with sm() as session:
            stmt = select(AdvSetting).where(AdvSetting.bot_active == True,
                                            AdvSetting.active_status == 'started')
            result = await session.execute(stmt)
            adv_settings: list[AdvSetting] = result.scalars().all()
            all_nmids = set()
            for adv in adv_settings:
                nmids = adv.nmids
                for nmid in nmids:
                    all_nmids.add(nmid)
            stmt = select(WBCard).where(WBCard.nmid.in_(all_nmids))
            wbcards: list[WBCard] = await session.stream(stmt)
            async for wbcard in  wbcards.scalars():
                try:
                    main_image_url: str = wbcard.photos[0]
                    async with aiohttp.ClientSession() as http_session:
                        async with http_session.get(main_image_url) as response:
                            image_bytes = await response.read()
                            pil_image = PilImage.open(BytesIO(image_bytes))
                    characteristics_word = await self._process_product_data(wbcard)
                    vector = await asyncio.to_thread(self._image_master.get_vector, pil_image)
                    dhash = await asyncio.to_thread(self._image_tools.dhash, pil_image)
                    logger.debug(f"Обновляем карточку: {wbcard.name}")
                    await self._gds.update_wb_card(wbcard, characteristics_word, dhash, vector)# Подтверждение изменений в базе данных
                except KeyError as exc:
                    if exc.args[0] == 'photos':
                        logger.debug(f"Карточка {wbcard.nmid} не содержит изображений, возможно, карточка не существует")
                    else:
                        logger.error(f"Ошибка при добавлении карточки в neo4j {wbcard.nmid}: {exc}")



    async def update_cards_in_graph(self):
        await self.update_cards_in_graph_for_shops()

    async def _process_product_data(self, wbcard: WBCard):
        product_data = wbcard.card_json
        # Обработка характеристик
        characteristics_words = {}
        for characteristic in product_data["characteristics"]:
            char_name = characteristic['name'].lower()
            char_value = characteristic['value']
            if not isinstance(char_value, list) or all(
                    self.is_number(x) for x in char_value):
                continue
            characteristics_words[char_name]: tuple(str, list[float]) = await self.__get_words_from_char_value(char_value)
        characteristics_words['name']: tuple(str, list[float])  = await self.__get_words_from_char_value(wbcard.name)
        if 'description' in characteristics_words:
            characteristics_words['description']: tuple(str, list[float]) = await self.__get_words_from_char_value(wbcard.description)
        return characteristics_words


    async def __get_words_from_char_value(self, char_value):
        if isinstance(char_value, list):
            char_value = " ".join(char_value)
        words = re.split(r'[ ,\.]+', char_value)
        words = list(filter(None, words))
        groups = []
        for word in words:
            word =  word.lower()
            word2vec = await self._word2vec.average_vector_from_sentence(word)
            groups.append((word, word2vec,))

        return groups


    @staticmethod
    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    async def update_predict_ctr(self, predicted: RedisEvent):
        await self._predictor.predict_ctr_for_keywords(predicted)

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


    async def update_all_data_in_db_run(self, tasks):
         wb_accesses = super_cabinet_manager.get_accesses_for_wb_cabinets()
         async for wb_access in wb_accesses:
             if wb_access.wb_cabinet.id not in tasks:
                 try:
                      shop_data_updater = ShopDataUpdater(wb_access)
                 except ApiForbiddenError:
                     logger.error(f'Нет нужных прав у токена')
                     continue
                 task = asyncio.create_task(shop_data_updater.update_all_data())
                 tasks[wb_access.wb_cabinet.id] = task
             else:
                 if tasks[wb_access.wb_cabinet.id].done():
                     if tasks[wb_access.wb_cabinet.id].exception():
                         logger.error(f'Ошибка обновления данных для Shop id {wb_access.wb_cabinet.shop_id}: {tasks[wb_access.wb_cabinet.id].exception()}, '
                                      f'{tasks[wb_access.wb_cabinet.id].exception()}')
                     else:
                         async with sm() as session:
                             wb_cabinet = wb_access.wb_cabinet
                             stmt = select(WBCabinet).where(WBCabinet.id == wb_cabinet.id)
                             result = await session.execute(stmt)
                             wb_cabinet = result.scalar()
                             wb_cabinet.last_update_all_data = datetime.datetime.now()
                             await session.commit()
                         logger.info('Задача обновления успешно выполнена')
                     del tasks[wb_access.wb_cabinet.id]

    async def check_accesses(self):
       await rights_control.check_all()



    async def shop_subscribe_control(self):
        while True:
            async with sm() as session:
                stmt = select(WBCabinet) \
                    .options(
                    selectinload(WBCabinet.wb_user_cabinets)\
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
            await asyncio.sleep(60*60)

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

    async def process_payment_for_advs(self):
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

    async def process_payment_for_parsing(self):
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

    async def process_payment_for_auto_bidder(self):
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



    async def run_bidder_process(self):
        wb_cabinet_tasks = {}
        adv_tasks = {}
        while True:
            accesses = super_cabinet_manager.get_accesses_for_bidder()
            async for access in accesses:
                cabinet_id = access.wb_cabinet.id
                if cabinet_id not in wb_cabinet_tasks:
                    task = asyncio.create_task(self._run_bidder_process_for_wb_cabinet(access,
                                                                                       adv_tasks = adv_tasks))
                    wb_cabinet_tasks[cabinet_id] = task

                else:
                    if wb_cabinet_tasks[cabinet_id].done():
                        logger.info(f'Задача обновления обновления ставок {cabinet_id}')
                        if wb_cabinet_tasks[cabinet_id].exception():
                            logger.error(
                                f'Ошибка обновления ставок: '
                                f'{wb_cabinet_tasks[cabinet_id].exception()},'
                                f' для кабинета {cabinet_id}'
                            )

                        del wb_cabinet_tasks[cabinet_id]
            await asyncio.sleep(0)

    async def _run_bidder_process_for_wb_cabinet(self, access: WBCabinetAccess, adv_tasks: dict):
        wb_api = WBApi(access)
        wb_cabinet = access.wb_cabinet
        async with sm() as session:
            stmt = select(AdvSetting)\
                .join(AdvSetting.wb_cabinet)\
                .where(WBCabinet.id == wb_cabinet.id,
                       AdvSetting.bidder_active == True,
                       AdvSetting.bot_active == True,
                       AdvSetting.active_status == 'started')
            result = (await session.execute(stmt)).unique()
            adv_settings = result.scalars().all()
        for adv_setting in adv_settings:
            if adv_setting not in adv_tasks:
                task = asyncio.create_task(self.run_bidder_process_for_adv(adv_setting.adv_id, wb_api))
                adv_tasks[adv_setting.id] = task
            else:
                if adv_tasks[adv_setting.id].done():
                    logger.info(
                        f'Задача управления ставкой завершена для кабинета '
                        f'{adv_setting.name}'
                    )
                    if adv_tasks[adv_setting.id].exception():
                        logger.error(
                            f'Ошибка обновления статистики ключей: '
                            f'{adv_tasks[adv_setting.id].exception()},'
                            f' для кабинета {adv_setting.name}'
                        )

                    del adv_tasks[adv_setting.id]
                    logger.info(f'Статистика ключевых слов для {adv_setting.name} обновлена')
                    logger.debug(f'Установка set для need_update_model')
        return

    async def run_bidder_process_for_adv(self, adv_id: int,
                                         wb_api: WBApi):
        async with sm() as session:
            stmt = select(AdvSetting)\
            .where(AdvSetting.adv_id == adv_id)
            result = await session.execute(stmt)
            adv_setting: AdvSetting = result.scalar()
            stmt = select(KeywordSetting)\
            .where(KeywordSetting.adv_setting_id == adv_setting.id,
                   KeywordSetting.hard_status == 2)
            result = await session.execute(stmt)
            white_adv_keywords: list[KeywordSetting] = result.scalars().all()
        max_position_for_adv = adv_setting.max_place
        max_cpm = adv_setting.max_cpm
        nmid_in_adv = adv_setting.nmids[0]
        promo_positions = []
        for keyword in white_adv_keywords:
            await parser.add_wb_positions(keyword.text, {nmid_in_adv})
            position = await redis_manager.get_keyword_position(keyword.text, nmid_in_adv)
            if not position:
                continue
            cpm_from_parsing: int = position.cpm
            if not cpm_from_parsing:
                continue
            promo_position = position.promo_position
            if not promo_position:
                continue
            promo_positions.append(promo_position)
        if promo_positions:
            fact_max_position: int = max(promo_positions)
            if fact_max_position == 1:
                new_cpm = cpm_from_parsing - 1
            elif fact_max_position < max_position_for_adv:
                new_cpm = cpm_from_parsing - 1
            elif fact_max_position > max_position_for_adv:
                new_cpm = cpm_from_parsing + 1

            if new_cpm > max_cpm:
                new_cpm = max_cpm
            elif new_cpm < 125:
                new_cpm = 125
            if new_cpm != cpm_from_parsing:
               await wb_api.advert.update_cpm(adv_id, new_cpm)



            
            
                
            
            







