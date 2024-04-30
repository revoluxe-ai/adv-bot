import asyncio
import datetime
import logging
import typing
from io import BytesIO
from itertools import product

import dask.dataframe as dd
import faiss
import joblib
import numpy as np
import pandas as pd
import pymystem3
from aiogram.client.session import aiohttp
from PIL import Image as PilImage
from sqlalchemy import and_
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload

from app.admin_bot.sender import messages, sender_manager
from app.admin_bot.sender import sender_manager as admin_sender
from app.client_bot.bot import bot
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.data_classes.namedtuples import (
    KeywordPhrase,
    KeywordStatForNeo,
)
from app.modules.common_slaves.wildberries.models import (
    AdvKeyword,
    AdvSetting,
    KeywordSetting,
    WBCabinet,
    WBCard, WBUserCabinet,
)
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.modules.wb_adv_updater import data_managers
from app.modules.wb_adv_updater.models import GlobalCategorySetting
from app.my_types import KeywordStat
from app.utils.db.session_maker import get_async_session_maker
from app.utils.faiss_manager.faiss_index_manager import FaissManager
from app.utils.image_master import image_tools
from app.utils.image_master.image_master2 import ImageMaster
from app.utils.NeoDataScience.driver import DataScience
from app.utils.text_master.Transformers import Word2Vec

from ..common_slaves.wildberries import super_cabinet_manager
from ..common_slaves.wildberries.exceptions import ApiForbiddenError
from ..common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from .ABC_manager import AbcManager
from .data_managers import DataGetter, DataSetter
from .graph_vector_updater import GraphUpdater
from .ML import Fitter, Predictor
from .shops_manager import rights_control

predictor = Predictor()


logger = logging.getLogger(__name__)


sm = get_async_session_maker()

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
        self._aiosm = get_async_session_maker()
        self._pymystem = pymystem3.Mystem()
        self._image_tools = image_tools


    @staticmethod
    async def update_keyword_stat(access: WBCabinetAccess, need_update_model:asyncio.Event):
        wb_api = WBApi(access)
        wb_cabinet = access.wb_cabinet
        async with sm() as session:
            stmt = select(AdvSetting).where(AdvSetting.wb_cabinet_id == wb_cabinet.id)
            result = (await session.execute(stmt)).unique()
            adv_settings = result.scalars().all()
            for adv_setting in adv_settings:
                keywords: list[KeywordStat] = await wb_api.advert.get_keywords_stat(adv_setting)
                logger.debug(f'Ключевые слова для {adv_setting.name} получены')
                for keyword in keywords:
                    stmt = select(AdvKeyword)\
                    .options(joinedload(AdvKeyword.keyword_setting))\
                    .where(and_(AdvKeyword.text == keyword.text,
                                                    AdvKeyword.date == keyword.date,
                                                    AdvKeyword.adv_setting_id == adv_setting.id))

                    keyword_db = await session.execute(stmt)
                    keyword_db: AdvKeyword = keyword_db.scalar()
                    if not keyword_db:
                        keyword_db = AdvKeyword()
                        stmt = select(KeywordSetting).where(and_(KeywordSetting.text == keyword.text,
                                                            KeywordSetting.adv_setting_id == adv_setting.id))
                        keyword_setting = await session.execute(stmt)
                        keyword_setting = keyword_setting.scalar()
                        if not keyword_setting:
                             keyword_setting = KeywordSetting()
                             keyword_setting.text = keyword.text
                             keyword_setting.adv_setting_id = adv_setting.id
                             session.add(keyword_setting)
                        keyword_db.keyword_setting = keyword_setting
                        keyword_db.adv_setting = adv_setting
                        keyword_db.text = keyword.text
                        keyword_db.date = keyword.date
                        session.add(keyword_db)

                    else:
                        if not keyword_db.keyword_setting:
                            stmt = select(KeywordSetting).where(and_(KeywordSetting.text == keyword.text,
                                                                     KeywordSetting.adv_setting_id == adv_setting.id))
                            keyword_setting = await session.execute(stmt)
                            keyword_setting = keyword_setting.scalar()
                            if not keyword_setting:
                                keyword_setting = KeywordSetting()
                                session.add(keyword_setting)
                                keyword_setting.text = keyword.text
                                keyword_setting.adv_setting_id = adv_setting.id
                            keyword_db.keyword_setting = keyword_setting
                        if any([keyword_db.views != keyword.views,
                                keyword_db.clicks != keyword.clicks]):
                            keyword_db.views = keyword.views
                            keyword_db.clicks = keyword.clicks
                            keyword_db.spend = keyword.spend
                await session.commit()
                await asyncio.sleep(0)
                logger.debug(f'Статистика ключевых слов для {adv_setting.name} обновлена')
                logger.debug(f'Установка set для need_update_model')
                need_update_model.set()



    async def graph_vector_update(self, update_model_on_new_features: asyncio.Event, predicted: asyncio.Event) -> None:

        length = 2**4
        await self.graph_updater.update_graph_run(length)
        await asyncio.sleep(1)
        await sender_manager.send_message_to_admin('Вектора обновлены')
        await sender_manager.send_message_to_admin('Ожидание предсказаний')
        # await predicted.wait() # это вроде как и не надо, без него работает
        await sender_manager.send_message_to_admin('Ожидание предсказаний пройдено')
        await self.graph_updater.get_nmids_and_keyword_featers_for_ml()
        await sender_manager.send_message_to_admin('Вектора для ML обновлены')
        update_model_on_new_features.set()

    def save_full_predict(self):
        # Загрузка данных с помощью Dask
        nmids_vectors = dd.read_csv(self.nmids_vectors_path)
        keyword_vectors = dd.read_csv(self.keywords_vectors_path)

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
    async def update_keywords_in_advs() -> list[typing.Awaitable]:
        update_tasks: dict[int, asyncio.Task] = {}
        while True:
            category_name_to_min_ctr = await data_managers.get_category_name_min_ctr_final_data()
            accesses  = super_cabinet_manager.get_accesses_for_wb_cabinets()
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
                        task = asyncio.create_task(data_setter.update_minus_keywords(adv_settings,
                                                                                     category_name_to_min_ctr))
                        update_tasks[wb_cabinet_id] = task
                else:
                    if update_tasks[wb_cabinet_id].done():
                        if update_tasks[wb_cabinet_id].exception():
                            logger.error(f'Ошибка обновления ключей: {update_tasks[wb_cabinet_id].exception()}')
                        del update_tasks[wb_cabinet_id]



    async def update_model(self, update_model_on_new_features):
        logger.debug('Старт обучения и сохранения модели')
        await self.fit_and_save_model(update_model_on_new_features)
        logger.debug('Устанавливаю сет, разрешаю обновление ключей')


    def __save_model( model, model_path):
        joblib.dump(model, model_path)


    async def fit_and_save_model(self, update_model_on_new_features):
        await self._fitter.getGradientBoostingFullFitModel(update_model_on_new_features)


    async def update_vectors_exec_mode(self, update_model_on_new_features: asyncio.Event, predicted: asyncio.Event,
                                       need_update_model):

        while True:
             await self.graph_vector_update(update_model_on_new_features, predicted)
             need_update_model.set()
             await asyncio.sleep(0)


    def __get_keyword_stat(self):
        kw_df = pd.read_csv(self.keyword_stat_df_path)
        return kw_df



    async def update_wb_adv_phrase_in_db(self, need_update_model):
        """update_model_on_new_features.set()"""
        while True:
            await self._update_wb_adv_phrase_in_db_bot_active()
            await sender_manager.send_message_to_admin('Все Фразы обновлены')
            need_update_model.set()
            await asyncio.sleep(0)


    async def _update_wb_adv_phrase_in_db_bot_active(self):
        await sender_manager.send_message_to_admin('Обновление фраз в neo4j')
        async with sm() as session:
            stmt = select(AdvSetting)\
            .filter(and_(AdvSetting.active_status == 'started',
                         AdvSetting.bot_active == True))
            result = await session.execute(stmt)
            adv_settings = result.unique().scalars().all()
            await sender_manager.send_message_to_admin('Кампании для обновления фраз получены')
            adv_setting_keyword_stats = {}
        for adv_setting in adv_settings:
            await sender_manager.send_message_to_admin(f'Получаем статистику ключей для {adv_setting.name}')
            keyword_stats = await data_managers.get_keywords_statistic(adv_setting, None)
            await sender_manager.send_message_to_admin(f'Статистика ключей для {adv_setting.name} получена')
            adv_setting_keyword_stats[adv_setting] = keyword_stats
        total_min_ctr = 0
        total_max_ctr = 100

        await sender_manager.send_message_to_admin('Получаем существующие фразы из neo')
        keyword_phrases_in_db = await self._gds.get_keyword_phrases()
        await sender_manager.send_message_to_admin('Существующие фразы из Neo получены')

        for adv_setting, keyword_stats in adv_setting_keyword_stats.items():
            phrase_data_list = []
            for keyword_stat in keyword_stats:
                if keyword_stat.text in keyword_phrases_in_db:
                    logger.debug(f'Фраза {keyword_stat.text} уже есть в базе данных')
                    await asyncio.sleep(0)
                    continue
                ctr = keyword_stat.ctr
                # Расчет нормализованного CTR для каждой фразы
                n_ctr = ((ctr - total_min_ctr) / (total_max_ctr - total_min_ctr)
                         if total_max_ctr > total_min_ctr else 0)
                words = keyword_stat.text.split()
                keywords = []
                for word in words:
                    vector = await self._word2vec.average_vector_from_sentence(word)
                    if vector is not None:
                        vector = list(vector)
                    keywords.append(KeywordStatForNeo(text=word, vector=vector))
                    await asyncio.sleep(0)

                phrase_data = KeywordPhrase(
                    text=keyword_stat.text,
                    ctr=n_ctr,
                    target_nmids=adv_setting.nmids if n_ctr > 0 else [] ,
                    words=keywords,
                    word2vec =  await self._word2vec.average_vector_from_sentence(keyword_stat.text)

                )
                phrase_data_list.append(phrase_data)
                await asyncio.sleep(0)

            await self._gds.add_keyword_phrase(phrase_data_list)
            await asyncio.sleep(0)
            await admin_sender.send_message_to_admin(f'Фразы для {adv_setting.name} добавлены')














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

    async def __update_cards_in_graph_for_shops(self):
        async with sm() as db_session:
            stmt = select(WBCard).where(WBCard.updated == False)
            result = await db_session.stream(stmt)
            async for wbcard in result.scalars():
                main_image_url: str = wbcard.photos[0]
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.get(main_image_url) as response:
                        image_bytes = await response.read()
                        pil_image = PilImage.open(BytesIO(image_bytes))

                vector = await asyncio.to_thread(self._image_master.get_vector, pil_image)
                dhash = await asyncio.to_thread(self._image_tools.dhash, pil_image)

                logger.debug(f"Обновляем карточку: {wbcard.name}")
                try:
                    characteristics_word = await self._process_product_data(wbcard)
                except Exception:
                    logger.error(f"Ошибка при обработке данных для карточки с именем: {wbcard.nmid}")
                    continue


                await self._gds.update_wb_card(wbcard, characteristics_word, dhash, vector)

                wbcard.updated = True  # Обновляем статус
                await db_session.commit()  # Подтверждение изменений в базе данных
                logger.debug(f"Статус 'updated' установлен в true для карточки с именем: {wbcard.name}")

    async def update_cards_in_graph(self):
       await self.__update_cards_in_graph_for_shops()

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
        return characteristics_words


    async def __get_words_from_char_value(self, char_value):
        if isinstance(char_value, list):
            char_value = " ".join(char_value)
        words = char_value.split()
        groups = []
        for word in words:
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

    async def update_predict_ctr(self, predicted: asyncio.Event):
        await self._predictor.predict_ctr_for_keywords( predicted)

    @staticmethod
    async def update_min_ctr_in_global_wb_category_settings():
        parent_categories_to_subcategories_name_list = await data_managers.get_parent_id_categories_subcategories_name_list()
        category_name_to_parent_id = {}
        for parent_id, subcategories in parent_categories_to_subcategories_name_list.items():
            for subcategory in subcategories:
                category_name_to_parent_id[subcategory] = parent_id
        wb_category_to_keywordstat_list = await data_managers.get_wb_category_to_keywordstat_list()
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
        percentile = 27
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

    async def update_all_data_in_db_run(self):
        tasks = {}
        while True:
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
                             logger.error(f'Ошибка обновления данных: {tasks[wb_access.wb_cabinet.id].exception()}')
                         del tasks[wb_access.wb_cabinet.id]

             await asyncio.sleep(30)

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
                ).where(
                    and_(
                        WBCabinet.expiration_time < datetime.datetime.now(),
                        WBCabinet.active is True
                    )
                )
                wb_cabinets_expirated_and_active = await session.execute(stmt)
                wb_cabinets_expirated_and_active = wb_cabinets_expirated_and_active.scalars().all()

                for wb_cabinet in wb_cabinets_expirated_and_active:
                    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet.id)
                    if not access:
                        wb_cabinet.active = False
                        logger.error('Нет активных токенов для кабинета')
                        await session.commit()
                        continue
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
                                wb_user_cabinet,
                            )()
                            logger.debug(f'Сообщение о просроченной подписке отправлено для юзера {user.username}')
                        except Exception as exc:
                            logger.error(
                                f'Ошибка при отправке сообщения о просроченной подписке '
                                f'для юзера {user.username}: {exc}'
                            )
                            await asyncio.sleep(1)
