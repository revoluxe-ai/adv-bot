import logging
import multiprocessing
import re
import typing
from datetime import datetime
from app.keyword_async_ml_updater import data_managers
from app.wildberries.api import WBApi
from collections import defaultdict
from functools import partial
from io import BytesIO
from itertools import product
import dask.dataframe as dd
import faiss
import joblib
import numpy as np
from PIL import Image as PilImage
import pandas as pd
from sqlalchemy import update, func
from aiogram.client.session import aiohttp
from sqlalchemy.future import select
from app.faiss_manager.faiss_index_manager import FaissManager
from app.session_maker import get_async_session_maker
from app.text_master.Transformers import Word2Vec
from . import data_managers
from .ABC_manager import AbcManager
from .data_managers import DataGetter, DataSetter
import asyncio
from .graph_vector_updater import GraphUpdater
from app.wildberries.data_classes.namedtuples import KeywordStatForNeo, KeywordPhrase
from ..db.associations import WBUserCabinet
# from ..shop_manager import ShopManager
from .ML import Fitter
from app.my_types import KeywordStat
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from app.NeoDataScience.driver import DataScience
from app.wildberries.models import (AdvSetting,
                                    AdvKeyword, WBCard,
                                    WBCabinet, WBToken)

from app.image_master.image_master2 import ImageMaster
import pymystem3
from app.image_master.image_tools import ImageTools
import asyncio
import pandas as pd
from sqlalchemy import and_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.future import select
from .ML import Predictor
from app.db.associations import WBUserCabinet
from app.keyword_async_ml_updater.models import ItemFeature, KeywordFeature
from app.my_types import WBCabinet
from app.telegram_bot.models import User
from app.wildberries.models import AdvSetting, AdvKeyword, KeywordSetting
from session_maker import get_async_session_maker

predictor = Predictor()


logger = logging.getLogger(__name__)

fit_logger = logging.getLogger('fit_logger')

sm = get_async_session_maker()




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
        self._image_tools = ImageTools()



    async def update_keyword_stat(self, cabinet:WBUserCabinet, need_update_model:asyncio.Event):
        wb_cabinet = cabinet.wb_cabinet
        wb_api = WBApi(cabinet)
        update_signal = False
        async with sm() as session:
            stmt = select(AdvSetting).where(AdvSetting.wb_cabinet_id == wb_cabinet.id)
            result = (await session.execute(stmt)).unique()
            for adv_setting in result.scalars():
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
                             keyword_db.keyword_setting = keyword_setting
                        session.add(keyword_db)
                        keyword_db.adv_setting = adv_setting
                        keyword_db.text = keyword.text
                        keyword_db.date = keyword.date
                        update_signal = True
                    else:
                        if not keyword_db.keyword_setting:
                            stmt = select(KeywordSetting).where(and_(KeywordSetting.text == keyword.text,
                                                                     KeywordSetting.adv_setting_id == adv_setting.id))
                            keyword_setting = await session.execute(stmt)
                            keyword_setting = keyword_setting.scalar()
                            if not keyword_setting:
                                keyword_setting = KeywordSetting()
                                keyword_setting.text = keyword.text
                                keyword_setting.adv_setting_id = adv_setting.id
                            keyword_db.keyword_setting = keyword_setting
                        if any([keyword_db.views != keyword.views,
                                keyword_db.clicks != keyword.clicks]):
                            update_signal = True
                    keyword_db.views = keyword.views
                    keyword_db.clicks = keyword.clicks
                    keyword_db.spend = keyword.spend
                    keyword_db.update_timestamp = keyword.update_timestamp
                    await session.merge(keyword_db)
                await session.commit()
                if update_signal:
                    need_update_model.set()
                    update_signal = False


    async def graph_vector_update(self, update_model_on_new_features: asyncio.Event, predicted: asyncio.Event) -> None:
        # power = self._shop_manager.power
        length = 2**4
        if True:
            await self.graph_updater.update_graph_run(length)
        await self.graph_updater.get_nmids_and_keyword_featers_for_ml(update_model_on_new_features, predicted)


    # async def update_cards(self, file_working:asyncio.Lock):
    #     loop = asyncio.get_event_loop()
    #     def get_shops():
    #         shops = self._shop_manager.get_all_shops()
    #         return shops
    #     shops = await loop.run_in_executor(None, get_shops)
    #     tasks = [self._data_getter.get_cards_for_shop(shop) for shop in shops]
    #     cards_list = await asyncio.gather(*tasks)
    #     cards = [card for sub_list in cards_list for card in sub_list]
    #     df = self._data_getter.get_nmid_offer_id_df(cards)
    #     # await self._gds.add_wb_cards(cards)
    #     await asyncio.sleep(60*60)


        #
        # def save_df(df, nmid_offer_id_shop_name_df_path):
        #     df.to_csv(nmid_offer_id_shop_name_df_path, index=False)
        #
        # async with file_working:
        #     await loop.run_in_executor(None, save_df, df, self.nmid_offer_id_shop_name_df_path)


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

    def __load_ml_model(self, model_path,):
        return joblib.load(model_path)


    async def update_keywords_in_advs(self) -> list[typing.Awaitable]:
            update_tasks: dict[int, asyncio.Task] = {}
            async  with sm() as session:
                category_name_to_min_ctr = await data_managers.\
                    get_category_name_min_ctr_final_data(session)
                subquery = select(AdvSetting.id).where(
                    AdvSetting.bot_active == True,
                    AdvSetting.wb_cabinet_id == WBCabinet.id
                ).exists()

                stmt = select(WBCabinet).options(
                    joinedload(WBCabinet.wb_user_cabinets).joinedload(WBUserCabinet.user)
                ).where(subquery)
                result = await session.execute(stmt)
                wb_cabinets: list[WBCabinet] = result.unique().scalars().all()

                for wb_cabinet in wb_cabinets:
                    if wb_cabinet.id not in update_tasks:
                        wb_user_cabinets: list[WBUserCabinet] = wb_cabinet.wb_user_cabinets
                        users: list[User] = [wb_user_cabinet.user for wb_user_cabinet in wb_user_cabinets]
                        tokens: list[WBToken] = [token for user in users for token in user.wb_tokens if token.shop_id == wb_cabinet.shop_id]
                        super_user = User()
                        super_user.wb_tokens = tokens
                        super_wb_user_cabinet = WBUserCabinet()
                        super_wb_user_cabinet.wb_cabinet = wb_cabinet
                        super_wb_user_cabinet.user = super_user
                        data_setter = DataSetter(super_wb_user_cabinet)
                        task = asyncio.create_task(data_setter.update_minus_keywords(category_name_to_min_ctr))
                        update_tasks[wb_cabinet.id] = task
                    else:
                        if update_tasks[wb_cabinet.id].done():
                            if update_tasks[wb_cabinet.id].exception():
                                logger.error(f'Ошибка обновления ключей: {update_tasks[wb_cabinet.id].exception()}')
                            del update_tasks[wb_cabinet.id]



    async def update_model(self, update_model_on_new_features):
        fit_logger.debug('Старт обучения и сохранения модели')
        await self.fit_and_save_model()
        fit_logger.debug('Устанавливаю сет, разрешаю обновление ключей')
        update_model_on_new_features.set()

    def __save_model(self, model, model_path):
        joblib.dump(model, model_path)


    async def fit_and_save_model(self):
        await self._fitter.getGradientBoostingFullFitModel()


    async def update_vectors_exec_mode(self, update_model_on_new_features: asyncio.Event, predicted: asyncio.Event):
        await self.graph_vector_update(update_model_on_new_features, predicted)




    def __get_keyword_stat(self):
        kw_df = pd.read_csv(self.keyword_stat_df_path)
        return kw_df

    async def update_wb_adv_phrase_in_db(self):
        async with sm() as session:
            stmt = select(AdvSetting)
            result = await session.execute(stmt)
            adv_settings = result.unique().scalars().all()
            adv_setting_keyword_stats = {}
            for adv_setting in adv_settings:
                keyword_stats = await data_managers.get_keyword_statistic(session, adv_setting)
                adv_setting_keyword_stats[adv_setting] = keyword_stats

            total_min_ctr = min([keyword_stat.ctr for keyword_stats in adv_setting_keyword_stats.values() \
             for keyword_stat in keyword_stats])
            total_max_ctr = max([keyword_stat.ctr for keyword_stats in adv_setting_keyword_stats.values() \
                for keyword_stat in keyword_stats])
            phrase_data_list = []
            for adv_setting, keyword_stats in adv_setting_keyword_stats.items():
                for keyword_stat in keyword_stats:
                    logger.debug(f'Обновление фразы в neo {keyword_stat.text} для кабинета {adv_setting.name}')
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

                    phrase_data = KeywordPhrase(
                        text=keyword_stat.text,
                        ctr=n_ctr,
                        target_nmids=adv_setting.nmids if n_ctr > 0 else [] ,
                        words=keywords,
                        word2vec =  await self._word2vec.average_vector_from_sentence(keyword_stat.text)

                    )
                    phrase_data_list.append(phrase_data)

            await self._gds.add_keyword_phrase(phrase_data_list)
            await asyncio.sleep(1)




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
        async with sm() as db_session:  # Предполагается использование асинхронной сессии
            stmt = select(WBCard).where(WBCard.updated == False)
            # Используем stream() для получения результатов как асинхронного генератора
            result = await db_session.stream(stmt)
            async for wbcard in result.scalars():
                if wbcard.updated:  # Проверяем, действительно ли нужно обновлять
                    continue

                main_image_url: str = wbcard.photos[0]
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.get(main_image_url) as response:
                        image_bytes = await response.read()
                        pil_image = PilImage.open(BytesIO(image_bytes))

                vector = await asyncio.to_thread(self._image_master.get_vector, pil_image)
                dhash = await asyncio.to_thread(self._image_tools.dhash, pil_image)

                logger.debug(f"Обновляем карточку: {wbcard.name}")
                characteristics_word = await self._process_product_data(wbcard)
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

    async def update_predict_ctr(self, update_model_on_new_features, predicted: asyncio.Event):
        await self._predictor.predict_ctr_for_keywords(update_model_on_new_features, predicted)












