import asyncio
import logging
from functools import wraps
from typing import TypeVar, ParamSpec, Any
from collections.abc import Callable, Awaitable

import neo4j
from neo4j import AsyncGraphDatabase

from app.modules.common_slaves.wildberries.data_classes.card_from_wb import CardFromWB
from app.modules.common_slaves.wildberries.data_classes.namedtuples import KeywordPhrase
from app.modules.common_slaves.wildberries.models import (
    WBCard,
    WBCategory,
)
from app.modules.wb_adv_updater import data_manager
from app.utils import redis_manager, text_cleaner

logger = logging.getLogger(__name__)


max_tries = 50
total_tries = 0

P = ParamSpec("P")
T = TypeVar("T")


def async_try_wrapper() -> (
    Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]
):
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            global total_tries
            global max_tries
            while True:
                try:
                    result = await func(*args, **kwargs)
                    total_tries = 0
                    return result
                except neo4j.exceptions.TransientError:
                    if max_tries > total_tries:
                        raise
                    else:
                        total_tries += 1
                        logger.debug(
                            "Ошибка взаимной блокировки, повтор транзакции через 5 сек"
                        )
                        await asyncio.sleep(5)

        return wrapper

    return decorator


class AsyncMeta(type):
    def __new__(cls, name: str, bases: tuple[type, ...], dct: dict[str, Any]) -> type:
        for key, value in dct.items():
            if callable(value) and asyncio.iscoroutinefunction(value):
                dct[key] = async_try_wrapper()(value)
        return super().__new__(cls, name, bases, dct)


class DataScience(metaclass=AsyncMeta):
    def __init__(self) -> None:
        import os

        self.MAIN_GRAPH_NAME = "main"
        name = os.environ.get("NEO4J_NAME")
        ip_address = os.environ.get("NEO4J_IP")
        port = os.environ.get("NEO4J_PORT")
        uri = f"bolt://{ip_address}:{port}"
        password = os.environ.get("NEO4J_PASSWORD")
        self.__uri: str = uri
        self.__auth: tuple[str | None, str | None] = (name, password)
        self.__driver = neo4j.GraphDatabase.driver(uri, auth=self.__auth)

        self.SHOP_GRAPH_NAME = "shop_graph"

    async def _graph_exists(self, graph_name: str) -> bool:
        query = """
        CALL gds.graph.exists($graph_name) YIELD exists
        RETURN exists
        """

        async def graph_exists(tx: Any, graph_name: str) -> bool:
            result = await tx.run(query, graph_name=graph_name)
            result = await result.single()
            return bool(result["exists"])

        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                result = await session.execute_read(graph_exists, graph_name)

        return result

    @staticmethod
    async def __drop_graph(tx: Any, graph_name: str) -> Any:
        result = await tx.run("CALL gds.graph.drop($graph_name)", graph_name=graph_name)
        return await result.single()

    async def drop_graph(self, graph_name: str) -> None:
        if await self._graph_exists(graph_name):
            async with AsyncGraphDatabase.driver(
                self.__uri, auth=self.__auth
            ) as driver:
                async with driver.session() as session:
                    result = await session.execute_write(self.__drop_graph, graph_name)

                logger.debug(result)

    async def linking_images_and_keyword(self) -> None:
        try:
            await self.linking_images()
        except neo4j.exceptions.ClientError as e:
            logger.error(f"Ошибка при склейке графа изображений {e}")
            del e
        try:
            await self.linking_keywords()
        except neo4j.exceptions.ClientError as e:
            logger.error(f"Ошибка при склейке графа ключевых слов {e}")
            del e

    async def linking_images(self) -> None:
        name = "images"
        await self._create_images_graph_if_not_exists(name)
        await self._set_knn_on_images(name)

    async def _create_images_graph_if_not_exists(self, name: str) -> None:
        async with neo4j.AsyncGraphDatabase.driver(
            self.__uri, auth=self.__auth
        ) as driver:
            async with driver.session() as session:

                async def transaction(tx: Any, name: str) -> Any:
                    # Проверяем, существует ли граф
                    result = await tx.run(
                        "CALL gds.graph.exists($name) YIELD exists", name=name
                    )
                    exists = await result.single()

                    # Если граф существует, удаляем его
                    if exists.value():
                        await tx.run("CALL gds.graph.drop($name)", name=name)

                    # Создаем граф
                    create_graph_query = """
                    CALL gds.graph.project(
                        $name,
                        { Image: {properties: 'vgg19'} },
                        "*" 
                    )
                    """
                    result = await tx.run(create_graph_query, name=name)
                    return await result.single()

                # Выполняем транзакцию
                result = await session.execute_write(transaction, name)
                logger.debug(result)

    async def _set_knn_on_images(self, name: str) -> None:
        async def execute_knn_process(tx: Any, name: str) -> None:
            stream_query = """
                               CALL gds.knn.stream(
                               $name,
                               {
                                   jobid: 'knn',
                                   nodeProperties: 
                                   {vgg19: 'COSINE'}
                               }
                           )
                           YIELD node1, node2, similarity
                           MATCH (source) WHERE id(source) = node1
                           MATCH (target) WHERE id(target) = node2
                           MERGE (source)-[r:LIKE]->(target)
                           ON CREATE SET r.dist = similarity
                           ON MATCH SET r.dist = similarity

                                        """
            stream_result = await tx.run(stream_query, name=name)
            await stream_result.consume()

        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                await session.execute_write(execute_knn_process, name)

    async def linking_keywords(self) -> None:
        name = "keywords"
        if await self._graph_exists(name):
            await self.drop_graph(name)
        await self._create_sub_graph_for_like_keyword(name)
        await self._set_knn_on_keywords(name)
        await self.drop_graph(name)

    async def _set_knn_on_keywords(self, name: str) -> None:
        stream_query = """
            CALL gds.knn.stream(
                $name,
                {
                    jobid: 'knn',
                    nodeProperties: 
                    {word2vec: 'COSINE'}
                }
            )
            YIELD node1, node2, similarity
            MATCH (source) WHERE id(source) = node1
            MATCH (target) WHERE id(target) = node2
            MERGE (source)-[r:LIKE]->(target)
            ON CREATE SET r.dist = similarity
            ON MATCH SET r.dist = similarity
            

        """

        async def execute_knn_process(tx: Any, name: str) -> None:
            # Записываем результаты в базу данных
            stream_result = await tx.run(stream_query, name=name)
            await stream_result.consume()

        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                await session.execute_write(execute_knn_process, name)

    async def update_fastrp(self, leingth: int) -> None:
        logger.debug("Обновление fastrp")
        await self.drop_graph(self.MAIN_GRAPH_NAME)
        logger.debug("Граф удален")
        await self.drop_graph(self.SHOP_GRAPH_NAME)
        logger.debug("Граф магазина удален")
        await self.create_base_graph(self.MAIN_GRAPH_NAME)
        logger.debug("Базовый граф создан")
        await self.fit_fastrp(self.MAIN_GRAPH_NAME, fastrp_vector_len=leingth)
        logger.debug("fastrp обучен")

    async def fit_fastrp(self, graph_name: str, fastrp_vector_len: int) -> None:
        query = """
        CALL gds.fastRP.write(
        $graph_name,
        {
            relationshipWeightProperty: 'dist',
            jobId: 'fastrp',
            embeddingDimension: $len,
            normalizationStrength: -1,
            iterationWeights: [1, 0.8, 0.5, 0.2, 0.1],
            writeProperty: 'fastrp',
            nodeSelfInfluence: 0.15,
            randomSeed: 1
            
        }
    )
    YIELD nodePropertiesWritten
    RETURN nodePropertiesWritten
        """

        async def fit_fastrp(tx: Any, graph_name: str, fastrp_vector_len: int) -> Any:
            result = await tx.run(query, graph_name=graph_name, len=fastrp_vector_len)
            return await result.single()

        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            result = await driver.session().execute_write(
                fit_fastrp, graph_name, fastrp_vector_len
            )

            logger.debug(result)

    async def create_base_graph(self, graph_name: str) -> None:
        query = """
            CALL gds.graph.project(
            $graph_name,
            {
                Item: {properties: []}, 
                Image: {properties: []},
                Keyword: {properties: []},
                KeywordPhrase: {properties: []},
                WBChar: {properties: []},
                Brand: {properties: []},
                WbCategory: {properties: []}
            },
            {
                IS: {
                    type: 'IS',
                    properties: {
                        dist: {
                            property: 'dist',
                            defaultValue:1
                        }
                    }
                },
                 LIKE: {
                    type: 'LIKE',
                    properties: {
                        dist: {
                            property: 'dist',
                            defaultValue: 1
                        }
                    }
                },


                 IN: {
                    type: 'IN',
                    properties: {
                        dist: {
                            property: 'dist',
                            defaultValue: 1
                        }
                    }
                }  

            }
        ) YIELD graphName, nodeProjection, nodeCount, relationshipProjection, relationshipCount, projectMillis
        RETURN graphName
                """

        async def create_base_graph(tx: Any, graph_name: str) -> Any:
            result = await tx.run(query, graph_name=graph_name)
            result = await result.data()
            return result

        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                result = await session.execute_write(create_base_graph, graph_name)
                logger.debug(result)

    async def add_keyword_phrase(self, phrase_data_list: list[KeywordPhrase]) -> Any:
        # Сериализация phrase_data в формат, подходящий для Cypher запроса
        data_list = []
        for phrase_data in phrase_data_list:
            if len(phrase_data.words) == 0:
                logger.error("Ошибка в фразе: нет слов")
            phrase_dict = {
                "text": phrase_data.text,
                "words": [
                    {"text": kw.text, "word2vec": kw.vector} for kw in phrase_data.words
                ],
                "dist_to_word": phrase_data.dist_to_word,
                "word2vec": phrase_data.word2vec,
            }
            data_list.append(phrase_dict)

        query = """
      UNWIND $data_list AS phrase
MERGE (keyword_phrase:KeywordPhrase {text: phrase.text})
ON CREATE SET keyword_phrase.word2vec = phrase.word2vec
ON MATCH SET keyword_phrase.word2vec = phrase.word2vec
WITH keyword_phrase, phrase
UNWIND phrase.words AS word
    MERGE (keyword:Keyword {text: word.text})
    ON CREATE SET keyword.word2vec = word.word2vec
    ON MATCH SET keyword.word2vec = word.word2vec
    MERGE (keyword_phrase)-[r:IS]->(keyword)
    ON CREATE SET r.dist = phrase.dist_to_word
    ON MATCH SET r.dist = phrase.dist_to_word
        """

        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                result = await session.execute_write(
                    lambda tx: tx.run(query, parameters={"data_list": data_list})
                )

        return result

    async def get_nmid_vectors(self, nmids: list[int]) -> list[tuple[int, list[float]]]:
        query = """
        MATCH (item:Item) WHERE  item.nmid  IN  $nmids 
        AND item.fastrp IS NOT NULL
        RETURN item.nmid as nmid, item.fastrp as vector
        """

        async def get_nmid_vectors(tx: Any, query: str, nmids: list[int]) -> Any:
            result = await tx.run(query, nmids=nmids)
            records = await result.data()
            return records

        async with neo4j.AsyncGraphDatabase.driver(
            self.__uri, auth=self.__auth
        ) as driver:
            async with driver.session() as session:
                records = await session.execute_read(
                    get_nmid_vectors, query, list(nmids)
                )

        data = []
        for record in records:
            vector = record["vector"]
            nmid = record["nmid"]
            if vector:
                data.append((nmid, vector))
            else:
                logger.debug(f"Вектор не найден для nmid: {nmid}")
        return data

    async def get_keywords_vectors(
        self,
    ) -> list[tuple[str, list[float]]]:
        query = """
        MATCH (k:KeywordPhrase) WHERE k.fastrp IS NOT NULL
        RETURN k.text as keyword, k.fastrp as vector
        """

        async def get_keywords_vectors(
            tx: Any, query: str
        ) -> list[tuple[str, list[float]]]:
            result = await tx.run(query)
            records = await result.data()
            data: list[tuple[str, list[float]]] = []
            for record in records:
                vector = record["vector"]
                keyword = record["keyword"]
                if vector:
                    data.append((keyword, vector))
            return data

        async with neo4j.AsyncGraphDatabase.driver(
            self.__uri, auth=self.__auth
        ) as driver:
            async with driver.session() as session:
                data = await session.execute_read(get_keywords_vectors, query)

        return data

    async def _create_sub_graph_for_like_keyword(self, graph_name: str) -> None:
        query = """
                MATCH (source:Keyword) WHERE NOT source.word2vec is Null
                WITH gds.graph.project(
                $graph_name,
                 source,
                  Null,
                {
                  sourceNodeProperties: {word2vec: source.word2vec},
                  targetNodeProperties: Null
                }
                
                ) AS g
                RETURN
             g.graphName AS graph, g.nodeCount AS nodes, g.relationshipCount AS rels
        """
        async with neo4j.AsyncGraphDatabase.driver(
            self.__uri, auth=self.__auth
        ) as driver:
            async with driver.session() as session:

                async def create_sub_graph(tx: Any, graph_name: str) -> Any:
                    result = await tx.run(query, graph_name=graph_name)
                    return await result.single()

                result = await session.execute_write(create_sub_graph, graph_name)
                logger.debug(result)

    async def get_status_job(self, jobid: str) -> Any:
        query = """
        call gds.listProgress($jobid) YIELD progress
        RETURN 	progress        
        """
        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                result = await session.execute_write(
                    lambda tx: tx.run(query, jobid=jobid)
                )
        return result

    def add_wb_cards(self, cards: list[CardFromWB]) -> None: ...

    async def update_wb_card(
        self,
        wbcard: WBCard,
        characteristics: dict[str, str],
        dhash: str,
        vector: list[float],
    ) -> None:
        nmid = wbcard.nmid
        wb_category: WBCategory = wbcard.wb_category
        category_name = wb_category.wb_category_name
        brand = wbcard.brand
        characteristics_list: list[list[Any]] = [
            [char, list(words)] for char, words in characteristics.items()
        ]

        query = """
            MERGE (item:Item {nmid: $nmid})
            MERGE (image:Image {dhash: $dhash})
            MERGE (item)-[:IN]->(image)
            SET image.vgg19 = $vector
            MERGE (category:WbCategory {name: $category_name})
            MERGE (item)-[:IS]->(category)
            MERGE (brand:Brand {name: $brand})
            MERGE (item)-[:IS]->(brand)
            WITH item, $characteristics AS characteristics  // Явно передаем item и characteristics
            UNWIND characteristics AS char
                MERGE (characteristic:WBChar {name: char[0]})
                MERGE (item)-[:IS]->(characteristic)
                WITH item, char[1] AS words, characteristic
                UNWIND words AS word_group
                    MERGE (keyword:Keyword {text: word_group[0]})
                    SET keyword.word2vec = word_group[1]
                    MERGE (characteristic)-[:IS]->(keyword)
            RETURN item
                            
            """

        async def update_wb_card(
            tx: Any,
            nmid: int,
            dhash: str,
            vector: list[float],
            category_name: str,
            brand: str,
            characteristics: list[list[Any]],
        ) -> Any:
            result = await tx.run(
                query,
                nmid=nmid,
                dhash=dhash,
                vector=vector,
                category_name=category_name,
                brand=brand,
                characteristics=characteristics,
            )
            return await result.data()

        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                await session.execute_write(
                    update_wb_card,
                    nmid,
                    dhash,
                    vector,
                    category_name,
                    brand,
                    characteristics_list,
                )

        logger.debug("Добавили карточку")

    async def get_keywords_vectors_by_keywords(
        self, keywords: list[str]
    ) -> list[tuple[str, list[float]]]:
        query = """
        MATCH (k:KeywordPhrase) WHERE k.text IN $keywords
        RETURN k.text as keyword, k.fastrp as vector
        """

        async def get_keywords_vectors_by_keywords(
            tx: Any, query: str, keywords: list[str]
        ) -> list[tuple[str, list[float]]]:
            result = await tx.run(query, keywords=keywords)
            records = await result.data()
            data: list[tuple[str, list[float]]] = []
            for record in records:
                vector = record["vector"]
                keyword = record["keyword"]
                if vector:
                    data.append((keyword, vector))
            return data

        async with neo4j.AsyncGraphDatabase.driver(
            self.__uri, auth=self.__auth
        ) as driver:
            async with driver.session() as session:
                data = await session.execute_read(
                    get_keywords_vectors_by_keywords, query, keywords
                )

        return data

    async def check_phrase_in_neo(self, text: str) -> Any:
        query = """
         MATCH (phrase:KeywordPhrase {text: $text}) 
         RETURN phrase.text as keyword
         """

        async def check_phrase(tx: Any, query: str, text: str) -> Any:
            result = await tx.run(query, text=text)
            return await result.single()

        async with neo4j.AsyncGraphDatabase.driver(
            self.__uri, auth=self.__auth
        ) as driver:
            async with driver.session() as session:
                result = await session.execute_read(check_phrase, query, text)
        return result

    async def __update_items_vectors(self) -> None:
        while True:
            try:
                await self._update_items_vectors_in_redis()
            except Exception as exc:
                logger.error(
                    f"Ошибка при обновлении векторов товаров в Redis: {exc}",
                    exc_info=True,
                )
            await asyncio.sleep(0)

    async def __update_keywords_vectors(self) -> None:
        while True:
            try:
                await self.update_keywords_vectors_process()
            except Exception as exc:
                logger.error(
                    f"Ошибка при обновлении векторов ключевых фраз в Redis: {exc}",
                    exc_info=True,
                )
            await asyncio.sleep(0)

    async def update_keywords_vectors_process(self) -> None:
        while True:
            try:
                await self._update_keywords_vectors_process()
            except Exception as exc:
                logger.error(
                    f"Ошибка при обновлении векторов ключевых фраз в Redis: {exc}",
                    exc_info=True,
                )
            await asyncio.sleep(5)

    async def _update_keywords_vectors_process(self) -> None:
        texts: set[str] = await data_manager.get_all_keywords_from_ch(last_days=7)
        clear_texts = [text_cleaner.clear(text) for text in texts]
        await self._update_keywords_vectors_in_redis(clear_texts)

    async def update_keywords_vectors(self) -> None:
        await self.__update_keywords_vectors()

    async def update_items_vectors(self) -> None:
        await self.__update_items_vectors()

    async def update_vectors_in_redis(self) -> None:
        """Удалили добавление ключей (вынесено в отдельную точку входа)"""
        await asyncio.gather(self.__update_items_vectors())

    async def _update_items_vectors_in_redis(self) -> None:
        query = """
        MATCH (item:Item)
        WHERE item.fastrp IS NOT NULL
        RETURN item.nmid as nmid, item.fastrp as vector
        """

        async def get_items_vectors(tx: Any, query: str) -> Any:
            result = await tx.run(query)
            records = await result.data()
            return records

        async with neo4j.AsyncGraphDatabase.driver(
            self.__uri, auth=self.__auth
        ) as driver:
            async with driver.session() as session:
                records = await session.execute_read(get_items_vectors, query)

        for record in records:
            nmid = record["nmid"]
            vector = record["vector"]
            try:
                await redis_manager.set_item_vector(nmid, vector)
            except Exception as exc:
                logger.error(
                    f"Ошибка при записи вектора товара в Redis: {exc}", exc_info=True
                )

    async def _update_keywords_vectors_in_redis(
        self, need_keywords_texts: list[str]
    ) -> None:
        query = """
        MATCH (k:KeywordPhrase)
        WHERE k.fastrp IS NOT NULL
        AND k.text IN $need
        RETURN k.text as keyword, k.fastrp as vector
        """

        async def get_keywords_vectors(
            tx: Any, query: str, need_keywords_texts: list[str]
        ) -> Any:
            result = await tx.run(query, need=need_keywords_texts)
            records = await result.data()
            return records

        async with neo4j.AsyncGraphDatabase.driver(
            self.__uri, auth=self.__auth
        ) as driver:
            async with driver.session() as session:
                records = await session.execute_read(
                    get_keywords_vectors, query, need_keywords_texts
                )

        for record in records:
            keyword = record["keyword"]
            vector = record["vector"]
            try:
                logger.debug("Начинаю писать вектор ключа в редис")
                await redis_manager.set_keyword_vector(keyword, vector)
                logger.debug("Записал вектор ключа в редис")
            except Exception as exc:
                logger.error(f"Ошибка при записи вектора ключевой фразы в Redis: {exc}")

    async def check_wb_card_in_neo(self, nmid: int) -> Any:
        query = """
        MATCH (item:Item) WHERE item.nmid = $nmid
        RETURN item
        """

        async def check_wb_card(tx: Any, query: str, nmid: int) -> Any:
            result = await tx.run(query, nmid=nmid)
            return await result.single()

        async with neo4j.AsyncGraphDatabase.driver(
            self.__uri, auth=self.__auth
        ) as driver:
            async with driver.session() as session:
                result = await session.execute_read(check_wb_card, query, nmid)
        return result
