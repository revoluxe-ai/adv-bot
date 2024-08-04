import asyncio
import logging
import typing
import neo4j
import yaml

from collections import defaultdict
from neo4j import AsyncGraphDatabase
from app.modules.common_slaves.wildberries.data_classes.card_from_wb import CardFromWB
from app.modules.common_slaves.wildberries.data_classes.namedtuples import KeywordPhrase
from app.modules.common_slaves.wildberries.models import WBCard, WBCategory
from python_modules.path_setting_funcs import get_setting_path

logger = logging.getLogger(__name__)

from functools import wraps

def async_semaphore_wrapper(semaphore):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            while True:
                try:
                    return await func(*args, **kwargs)
                except neo4j.exceptions.TransientError:
                    logger.error('Ошибка взаимной блокировки, повтор транзакции через 5 сек')
                    await asyncio.sleep(5)

        return wrapper
    return decorator

class AsyncMeta(type):
    def __new__(cls, name, bases, dct):
        semaphore = asyncio.Semaphore(3)
        for key, value in dct.items():
            if callable(value) and asyncio.iscoroutinefunction(value):
                dct[key] = async_semaphore_wrapper(semaphore)(value)
        return super().__new__(cls, name, bases, dct)





class DataScience(metaclass=AsyncMeta):
    def __init__(self):
        self.MAIN_GRAPH_NAME = 'main'
        setting_path = get_setting_path()
        with open(setting_path, 'r', encoding='utf-8') as file:
            setting  = yaml.safe_load(file)
        name = setting['neo4j']['name']
        password = setting['neo4j']['password']
        self.__uri: str = setting['neo4j']['uri']
        self.__auth: tuple[str, str] = (name, password)
        self.__driver = neo4j.GraphDatabase.driver(self.__uri, auth=self.__auth)



        self.SHOP_GRAPH_NAME = 'shop_graph'


    def get_keyword_phrase_vector_by_id(self, id_):
        query = """
        MATCH (phrase:KeywordPhrase ) WHERE
        id(phrase) = $id_
        RETURN phrase.text as text
        """


        with self._neo_driver.driver.session() as s:
            vector = s.run(query, id_=id_).single()['text']

        return vector


    def set_direct_dist_item_to_keywords(self, offer_ids: list[str]):

       query = """
        MATCH(source: Item
        {offer_id: $offer_id})
        CALL
        gds.allShortestPaths.delta.write(
            $g_name,
            {  
                sourceNode: id(source),
                relationshipWeightProperty: 'dist',
                writeRelationshipType: 'DIRECT_DIST'
            }
        )
        YIELD
        relationshipsWritten,
        preProcessingMillis,
        computeMillis,
        postProcessingMillis,
        writeMillis,
        configuration
        RETURN relationshipsWritten

       """


       with self._neo_driver.driver.session() as s:
           for n, offer_id in enumerate(offer_ids):
               print(n)
               result = s.run(query, offer_id = offer_id[0], g_name = self.MAIN_GRAPH_NAME).data()
               logger.debug(result)

    def create_graph(self, graph_name, properties_for_all_nodes:list[str]):
        query = """
    CALL gds.graph.project(
    $graph_name,
    {
        Item: {properties: $properties}, 
        Image: {properties: $properties},
        Keyword: {properties: $properties},
        KeywordPhrase: {properties: $properties}
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

        with self._neo_driver.driver.session() as s:
            result = s.run(query, graph_name = graph_name,
                           properties = properties_for_all_nodes).single()
            logger.debug(f'Граф создан: {result.data()}')


    async def _graph_exists(self, graph_name):
        query = """
        CALL gds.graph.exists($graph_name) YIELD exists
        RETURN exists
        """
        async def graph_exists(tx, graph_name):
            result = await tx.run(query, graph_name=graph_name)
            result =  await result.single()
            return result['exists']


        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                result = await session.read_transaction(
                    graph_exists, graph_name)

        return result

    @staticmethod
    async def __drop_graph(tx, graph_name):
        result = await tx.run(
            "CALL gds.graph.drop($graph_name)", graph_name=graph_name
        )
        return await result.single()

    async def drop_graph(self, graph_name):
        if await self._graph_exists(graph_name):
            async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
                async with driver.session() as session:
                     result = await session.write_transaction(self.__drop_graph, graph_name)

                logger.debug(result)







    def get_mean_distance(self, offer_id: str, phrase: list)-> float:
        query = """
        match (item:Item {offer_id: $offer_id})-[r:DIRECT_DIST]-(keyword:Keyword)
        WHERE
        keyword.text in $phrase
        RETURN 
        //item.offer_id as offer_id, 
        avg(r.totalCost) as totalCost
        //collect(keyword.text) as phrase
        """

        s = self._neo_driver.driver.session()
        result =  s.run(query, offer_id = offer_id, phrase = phrase).single()
        totalCost = result['totalCost']
        s.close()
        return totalCost

    def set_dist_on_null_rels(self):
        self._set_dist_for_rels_image_from_item()
        self._set_dist_for_rels_item_from_image()
        self._set_dist_for_rels_keyword_from_image()
        self._set_dist_for_rels_image_from_keyword()
        self._set_dist_rels_for_item_from_keyword()
        self._set_dist_rels_for_keyword_from_item()

    def _set_dist_for_rels_image_from_item(self):
        query = """
        MATCH (image:Image)<-[r:IS]-(:Item)
                WITH count(r) as total_rels
                MATCH (image:Image)<-[r:IS]-(:Item)
                WITH image, COLLECT(r) as rels, count(r) as rels_loc, total_rels
                FOREACH (rel in rels | SET rel.dist = toFloat(rels_loc) / total_rels)
                RETURN image.image_id, rels_loc, total_rels

        """
        with self._neo_driver.driver.session() as s:
             s.run(query).single()

    def _set_dist_for_rels_item_from_image(self):
        query = """
          MATCH (item:Item)<-[r:IS]-(:Image)
                WITH count(r) as total_rels
                MATCH (item:Item)<-[r:IS]-(:Image)
                WITH item, COLLECT(r) as rels, count(r) as rels_loc, total_rels
                FOREACH (rel in rels | SET rel.dist = toFloat(rels_loc) / total_rels)
                RETURN item.offer_id, rels_loc, total_rels
               """
        with self._neo_driver.driver.session() as s:
            s.run(query).single()

    def _set_dist_for_rels_keyword_from_image(self):
        query = """
        MATCH (keyword:Keyword)<-[r:IS]-(:Image)
                WITH count(r) as total_rels
                MATCH (keyword:Keyword)<-[r:IS]-(:Image)
                WITH keyword, COLLECT(r) as rels, count(r) as rels_loc, total_rels
                FOREACH (rel in rels | SET rel.dist = toFloat(rels_loc) / total_rels)
                RETURN keyword.text, rels_loc, total_rels
        """
        with self._neo_driver.driver.session() as s:
            s.run(query).single()

    def _set_dist_for_rels_image_from_keyword(self):
        query = """
        MATCH (image:Image)<-[r:IS]-(:Keyword)
                WITH count(r) as total_rels
                MATCH (image:Image)<-[r:IS]-(:Keyword)
                WITH image, COLLECT(r) as rels, count(r) as rels_loc, total_rels
                FOREACH (rel in rels | SET rel.dist = toFloat(rels_loc) / total_rels)
                RETURN image.image_id, rels_loc, total_rels
               """
        with self._neo_driver.driver.session() as s:
            s.run(query).single()

    def _set_dist_rels_for_item_from_keyword(self):
        query = """
        MATCH (item:Item)<-[r:IS]-(:Keyword)
                WITH count(r) as total_rels
                MATCH (item:Item)<-[r:IS]-(:Keyword)
                WITH item, COLLECT(r) as rels, count(r) as rels_loc, total_rels
                FOREACH (rel in rels | SET rel.dist = toFloat(rels_loc) / total_rels)
                RETURN item.offer_id, rels_loc, total_rels
                       """
        with self._neo_driver.driver.session() as s:
            s.run(query).single()

    def _set_dist_rels_for_keyword_from_item(self):
        query = """
              MATCH (keyword:Keyword)<-[r:IS]-(:Item)
                WITH count(r) as total_rels
                MATCH (keyword:Keyword)<-[r:IS]-(item:Item)
                WITH keyword, COLLECT(r) as rels, count(r) as rels_loc, total_rels
                FOREACH (rel in rels | SET rel.dist = toFloat(rels_loc) / total_rels)
                RETURN keyword.text, rels_loc, total_rels

                               """
        with self._neo_driver.driver.session() as s:
            s.run(query).single()

    def get_knn(self, offer_id, property):
        query = f"""
        match (i:Item {{offer_id: $offer_id}})-[r:KNN]-(i1:Item) 
        
        return i.offer_id, r.{property}, i1.offer_id
        ORDER BY r.{property} DESC
        """
        with self._neo_driver.driver.session() as s:
            result = s.run(query, offer_id = offer_id, property = property).data()
        return result


    def write_knn(self,  graph_name,
                labels=['Item', 'Image', 'Keyword'],
                rels=['IS', 'LIKE', 'IN'],
                topK=50,
                jobid='knn', property='fastrp'):
        query = f"""
        CALL gds.knn.write(
          $name,
          {{
             nodeLabels: $labels,
             relationshipTypes: $rels,
             jobId: $jobid,
             nodeProperties: {{{property}: 'EUCLIDEAN'}},
             topK: $topK,
             writeRelationshipType: 'KNN',
             writeProperty: '{property}'
          }}
        ) 
        """

        with self._neo_driver.driver.session() as s:
            s.run(query, name=graph_name,
                           labels=labels,
                           rels=rels,
                           topK=topK,
                           jobid=jobid)

    def create_shop_graph(self, offer_ids):
        query = """
        MATCH (source:Item) WHERE source.offer_id in $offer_ids
        OPTIONAL MATCH (source)-->(target:None)
        WITH gds.graph.project(
        $graph_name,
        source,
        target,
        {
        sourceNodeProperties: source {fastrp_32: source.fastrp_32},
        targetNodeProperties: Null
        }
        ) AS g
         RETURN g.graphName AS graph, g.nodeCount AS nodes
    """

        with self._neo_driver.driver.session() as s:
            result = s.run(query, graph_name= self.SHOP_GRAPH_NAME,
                           offer_ids = offer_ids
                           ).data()
            logger.debug(result)
            print(f"""Граф  создан""")

    async def linking_images_and_keyword(self):
       # await self.linking_images()
       await self.linking_keywords()


    async def linking_images(self):
        name = 'images'
        await self._create_images_graph_if_not_exists(name)
        await self._set_knn_on_images(name)


    @staticmethod
    async def __create_graph_if_not_exists(tx, name):
        result = await tx.run(
            "CALL gds.graph.exists($name) YIELD exists RETURN exists", name=name
        )
        record = await result.single()
        exists = record['exists']
        return exists

    async def _create_images_graph_if_not_exists(self, name):
        async with neo4j.AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                async def transaction(tx, name):
                    # Проверяем, существует ли граф
                    result = await tx.run("CALL gds.graph.exists($name) YIELD exists", name=name)
                    exists = await result.single()

                    # Если граф существует, удаляем его
                    if exists.value():
                        await tx.run('CALL gds.graph.drop($name)', name=name)

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
                result = await session.write_transaction(transaction, name)
                logger.debug(result)

    async def _set_knn_on_images(self, name):

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




        async def execute_knn_process(tx, name):
            # Выполняем mutate
            # Записываем результаты в базу данных
            stream_result = await tx.run(stream_query, name=name)
            await stream_result.consume()


        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                result = await session.write_transaction(execute_knn_process, name)
                logger.debug(result)

        return "KNN relationships for images updated successfully"




    async def linking_keywords(self):
        name = 'keywords'
        await self.drop_graph(name)
        await self._create_sub_graph_for_like_keyword(name)
        if  await self._graph_exists(name):
            await self._set_knn_on_keywords(name)
        await self.drop_graph(name)


    def _create_keywords_graph_if_not_exists(self, name):
        if not self.gds.graph.exists(name).iloc[1]:
            query = """
            MATCH (source:Keyword)
            WHERE source.word2vec is not null
            OPTIONAL MATCH (source)--(target:Null)
            WITH gds.graph.project($name, source, target,
            {sourceNodeProperties: source { word2vec: source.word2vec},
            targetNodeProperties: null}

            ) AS g
            RETURN
  g.graphName AS graph, g.nodeCount AS nodes, g.relationshipCount AS rels

            """
            with self._neo_driver.driver.session() as s:
                result = s.run(query, name=name)
                logger.debug(result)

    async def _set_knn_on_keywords(self, name):
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

        async def execute_knn_process(tx, name):
            # Записываем результаты в базу данных
            stream_result = await tx.run(stream_query, name=name)
            await stream_result.consume()


        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                result = await session.write_transaction(execute_knn_process, name)
                logger.debug(result)

        return "KNN relationships for keywords updated successfully"







    def get_near_offer_ids(self, card, free_offer_ids, topK):
        query ="""
        MATCH (source_item:Item {offer_id: $offer_id})
        -[r:KNN]->(target_item:Item) WHERE target_item.offer_id in $offer_ids
        RETURN target_item.offer_id as offer_id  ORDER BY r.dist DESC 
        LIMIT $topK
        """

        with self._neo_driver.driver.session() as s:
            result = s.run(query, offer_id = card.offer_id,
                           offer_ids = free_offer_ids,
                           topK = topK).value("offer_id")

        return result

    def get_k_mean_groups(self, k):
        logger.debug('Начинаю запрос')
        query = """
       CALL gds.kmeans.stream(
          'knn',
          {
              nodeProperty: 'fastrp',
              k: $k,
              maxIterations: 100,
              deltaThreshold: 0.001
          }
        )
        YIELD nodeId, communityId, distanceFromCentroid, silhouette
        MATCH (node) WHERE id(node) = nodeId
        RETURN node.offer_id AS offer_id, communityId as group
        """

        with self._neo_driver.driver.session() as s:
            result = s.run(query, k = k).data()
        logger.debug('Запрос выполнен')
        result_dict = defaultdict(list)

        for part in result:
            group = part['group']
            offer_id = part['offer_id']
            result_dict[group].append(offer_id)
        groups = result_dict.values()
        return groups



    def get_near_offer_ids_by_keyword(self, keyword,  filter_offer_ids, limit):
        query = """
        MATCH (k:Keyword {text: $keyword})<-[r*1..2]-(:Image)<-[:IN]-(item:Item)
        WHERE item.offer_id in  $filter_offer_ids
            WITH item.offer_id AS offer_id,
            REDUCE(s = 1, rel IN r | s * COALESCE(rel.dist, 1)) AS multiplication_result
            RETURN offer_id
            ORDER BY multiplication_result DESC LIMIT $limit
        """

        with self._neo_driver.driver.session() as s:
            result = s.run(query, keyword = keyword,
                    filter_offer_ids = filter_offer_ids,
                           limit = limit).value('offer_id')

        return result

    async def update_fastrp(self, leingth):
        await self.drop_graph(self.MAIN_GRAPH_NAME)
        await self.drop_graph(self.SHOP_GRAPH_NAME)
        await self.create_base_graph(self.MAIN_GRAPH_NAME)
        await self.fit_fastrp(self.MAIN_GRAPH_NAME, fastrp_vector_len = leingth)




    def set_knn_for_items_by_fastrp(self, graph_name, topK):
         query = """
         CALL gds.knn.write(
                  $graph_name,
                  {
                     nodeLabels: ['Item'],
                     relationshipTypes:  ['*'],
                     jobId: 'knn',
                     nodeProperties: {fastrp: 'EUCLIDEAN'},
                     topK: $topK,
                     writeRelationshipType: 'KNN',
                     writeProperty: 'dist'
                  }
                )    YIELD  nodesCompared RETURN nodesCompared"""
         with self._neo_driver.driver.session() as s:
             result = s.run(query, graph_name = graph_name,
                            topK = topK).data()
             logger.debug(result)



    async def fit_fastrp(self, graph_name, fastrp_vector_len):
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
        async def fit_fastrp(tx, graph_name, fastrp_vector_len):
            result = await tx.run(query, graph_name=graph_name, len=fastrp_vector_len)
            return await result.single()

        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            result = await driver.session().write_transaction(fit_fastrp, graph_name, fastrp_vector_len)

            logger.debug(result)




    async def create_base_graph(self, graph_name):
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
        async def create_base_graph(tx, graph_name):
            result = await tx.run(query, graph_name=graph_name)
            return await result.single()

        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                result = await session.write_transaction(create_base_graph, graph_name)
                logger.debug(result)


    #
    # def create_shop_graph_for_item_knn(self, graph_name, offer_ids):
    #      query = """
    #       MATCH (source:Item) WHERE source.offer_id in $offer_ids
    #     OPTIONAL MATCH (source)-->(target:None)
    #     WITH gds.graph.project(
    #     $graph_name,
    #     source,
    #     target,
    #     {
    #     sourceNodeProperties: {fastrp: source.fastrp},
    #     targetNodeProperties: Null,
    #     sourceNodeLabels: ['Item'],
    #     targetNodeLabels: Null
    #
    #     }
    #     ) AS g
    #      RETURN g.graphName AS graph, g.nodeCount AS nodes
    #
    #      """
    #
    #      with self._neo_driver.driver.session() as s:
    #          result = s.run(query, graph_name = graph_name, offer_ids = offer_ids).data()
    #          logger.debug(result)



    # def get_items_count(self):
    #     query = """
    #     MATCH (item:Item)
    #     return count(item) AS count
    #     """
    #
    #     with self._neo_driver.driver.session() as s:
    #         result = s.run(query).single()
    #
    #     return result['count']
    #
    # def add_unknow_keyword(self, unknown_keyword:str, target_keyword:str, dist:float):
    #     query = """
    #     MERGE (unknow:Keyword {text: $unknow})
    #     MERGE (target:Keyword {text: $unknow})
    #     MERGE (unknow)-[r:LIKE]->(targer)
    #     SET r.dist = $dist
    #     """
    #
    #     with self._neo_driver.driver.session() as s:
    #         result = s.run(query, unknow = unknown_keyword,
    #                        target = target_keyword,
    #                        dist = dist)
    #
    #         logger.debug(result)

    async def add_keyword_phrase(self, phrase_data_list: list[KeywordPhrase]):
        # Сериализация phrase_data в формат, подходящий для Cypher запроса
        data_list = []
        for phrase_data in phrase_data_list:
            phrase_dict = {
                'text': phrase_data.text,
                'words': [{'text': kw.text, 'word2vec': kw.vector} for kw in phrase_data.words],
                'dist_to_word': phrase_data.dist_to_word,
                'word2vec': phrase_data.word2vec
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
                result = await session.write_transaction(
                    lambda tx: tx.run(query, parameters = {'data_list': data_list}))

        return result




    # def create_graph_for_keyword_phrase_knn(self, graph_name):
    #     query = """
    #         CALL gds.graph.project(
    #         $graph_name,
    #         {
    #
    #             KeywordPhrase: {properties: ['fastrp']}
    #         },
    #         {
    #             IS: {
    #                 type: 'IS',
    #                 properties: {
    #                     dist: {
    #                         property: 'dist',
    #                         defaultValue:1
    #                     }
    #                 }
    #             },
    #              LIKE: {
    #                 type: 'LIKE',
    #                 properties: {
    #                     dist: {
    #                         property: 'dist',
    #                         defaultValue: 1
    #                     }
    #                 }
    #             },
    #
    #
    #              IN: {
    #                 type: 'IN',
    #                 properties: {
    #                     dist: {
    #                         property: 'dist',
    #                         defaultValue: 1
    #                     }
    #                 }
    #             }
    #
    #         }
    #     ) YIELD graphName, nodeProjection, nodeCount, relationshipProjection, relationshipCount, projectMillis
    #     RETURN graphName
    #             """
    #     with self._neo_driver.driver.session() as s:
    #         result = s.run(query, graph_name=graph_name)
    #         logger.debug(result)

    # def set_knn_for_keyword_phrase_by_fastrp(self, graph_name, topK):
    #     query = """
    #           CALL gds.knn.write(
    #                    $graph_name,
    #                    {
    #                       nodeLabels: ['KeywordPhrase'],
    #                       relationshipTypes:  ['*'],
    #                       jobId: 'knn',
    #                       nodeProperties: {fastrp: 'EUCLIDEAN'},
    #                       topK: $topK,
    #                       writeRelationshipType: 'KNN',
    #                       writeProperty: 'dist'
    #                    }
    #                  )    YIELD  nodesCompared RETURN nodesCompared"""
    #     with self._neo_driver.driver.session() as s:
    #         result = s.run(query, graph_name=graph_name,
    #                        topK=topK).data()
    #         logger.debug(result)

    async def get_nmid_vectors(self,  nmids: list[int]) -> typing.List[typing.Tuple[int, typing.List[float]]]:
        query = """
        MATCH (item:Item) WHERE  item.nmid  IN  $nmids 
        AND item.fastrp IS NOT NULL
        RETURN item.nmid as nmid, item.fastrp as vector
        """
        async def get_nmid_vectors(tx, query, nmids):
            result = await tx.run(query, nmids=nmids)
            records = await result.data()
            return records


        async with neo4j.AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                records = await session.read_transaction(get_nmid_vectors, query, list(nmids))

        data = []
        for record in records:
            vector = record['vector']
            nmid = record['nmid']
            if vector:
                data.append((nmid, vector))
            else:
                logger.debug(f'Вектор не найден для nmid: {nmid}')
        return data

    async def get_keywords_vectors(self) -> typing.List[typing.Tuple[str, typing.List[float]]]:
        query = """
        MATCH (k:KeywordPhrase) WHERE k.fastrp IS NOT NULL
        RETURN k.text as keyword, k.fastrp as vector
        """

        async def get_keywords_vectors(tx, query):
            result = await tx.run(query)
            records = await result.data()
            data = []
            for record in records:
                vector = record['vector']
                keyword = record['keyword']
                if vector:
                    data.append((keyword, vector))
            return data


        async with neo4j.AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                 data = await session.read_transaction(get_keywords_vectors, query)


        return data



    # def get_all_keyword_phrases(self):
    #     query = """
    #     MATCH (phrase:KeywordPhrase)
    #     RETURN phrase.text as keyword
    #     """
    #     with self._neo_driver.driver.session() as s:
    #         result = s.run(query).values('keyword')
    #     result = [r[0] for r in result]
    #     return result
    #
    # def get_keyword_phrases_without_vector(self):
    #     query = """
    #     MATCH (k:KeywordPhrase) WHERE k.fastrp IS NULL
    #     RETURN COUNT (k) AS count
    #     """
    #
    #     with self._neo_driver.driver.session() as s:
    #         result = s.run(query).single()
    #     return result['count']

    async def _create_sub_graph_for_like_keyword(self, graph_name):
        query = """
             MATCH (source:Keyword)
            WHERE source.word2vec IS NOT NULL
          OPTIONAL MATCH (source)-->(target:None)
        WITH gds.graph.project(
        $graph_name,
        source,
        target,
        {
        sourceNodeProperties: source {word2vec: source.word2vec},
        targetNodeProperties: Null
        }
        ) AS g
         RETURN g.graphName AS graph, g.nodeCount AS nodes
        """
        async with neo4j.AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                async def create_sub_graph(tx, graph_name):
                    result = await tx.run(query, graph_name=graph_name)
                    return await result.single()

                result = await session.write_transaction(create_sub_graph, graph_name)
                logger.debug(result)









    # def add_keyword_phrase_without_item(self, phrase_data: KeywordPhrase):
    #     # Предполагается, что kw.vector уже в формате списка чисел. Если нет, необходимо его преобразовать.
    #     phrase_dict = {
    #         'text': phrase_data.text,
    #         'words': [{'word': word.text, 'vector': list(word.vector) if word.vector is not None else None} \
    #                   for word in phrase_data.words],
    #         # Преобразование vector в список, если это необходимо
    #         'dist_to_word': phrase_data.dist_to_word
    #     }
    #
    #     query = """
    #         MERGE (keyword_phrase:KeywordPhrase {text: $text})
    #         WITH keyword_phrase, $words AS words, $dist_to_word AS dist_to_word
    #              UNWIND words AS wordData
    #                  MERGE (keyword:Keyword {text: wordData.word})
    #                  ON CREATE SET keyword.word2vec = wordData.vector
    #                  ON MATCH SET keyword.word2vec = wordData.vector
    #                  MERGE (keyword_phrase)-[rk2k:LIKE]->(keyword)
    #                  ON CREATE SET rk2k.dist = dist_to_word
    #                  ON MATCH SET rk2k.dist = dist_to_word
    #                  MERGE (keyword_phrase)<-[rk2k_1:LIKE]-(keyword)
    #                  ON CREATE SET rk2k_1.dist = dist_to_word
    #                  ON MATCH SET rk2k_1.dist = dist_to_word
    #          """
    #     while True:
    #         try:
    #             with self._neo_driver.driver.session() as s:
    #                 # Распаковка phrase_dict в качестве именованных параметров запроса
    #                 result = s.run(query, **phrase_dict)
    #                 logger.debug(result)
    #                 break
    #         except Exception as exc:
    #             logger.error(exc)
    #             time.sleep(5)

    async def get_status_job(self, jobid):
        query = """
        call gds.listProgress($jobid) YIELD progress
        RETURN 	progress        
        """
        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                result = await session.write_transaction(
                    lambda tx: tx.run(query, jobid=jobid))
        return result

    def add_wb_cards(self, cards:list[CardFromWB]):
        ...

    async def update_wb_card(self, wbcard:WBCard, characteristics:dict[str, str],
                             dhash: str,
                             vector: list[float]):

        nmid = wbcard.nmid
        wb_category: WBCategory = wbcard.wb_category
        category_name = wb_category.wb_category_name
        brand = wbcard.brand
        characteristics = [[char, list(words)] for char, words in characteristics.items()]

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

        async def update_wb_card(tx, nmid, dhash, vector, category_name, brand, characteristics):
            result = await tx.run(query, nmid=nmid, dhash=dhash, vector=vector, category_name=category_name,
                            brand=brand, characteristics=characteristics)
            return await result.data()

        async with AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                result = await session.write_transaction(update_wb_card,
                                                         nmid,
                                                         dhash,
                                                         vector,
                                                         category_name,
                                                         brand,
                                                         characteristics)

        logger.debug(result)

    async def get_keyword_phrases(self) -> list[str]:
        query = """
        MATCH (phrase:KeywordPhrase)
        RETURN phrase.text as keyword
        """
        async def get_keyword_phrases(tx, query):
            result = await tx.run(query)
            records = await result.data()
            return [record['keyword'] for record in records]

        async with neo4j.AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                data = await session.read_transaction(get_keyword_phrases, query)

        return data

    async def clear_cards_in_neo4j(self, need_nmids: list[int]):
        query = """
    CALL apoc.periodic.iterate(
    "MATCH (item:Item) WHERE NOT item.nmid IN $need_nmids RETURN item",
    "DETACH DELETE item",
    {batchSize: 100, params: {need_nmids: $need_nmids}}
)
        """
        async def clear_cards(tx, query, need_nmids):
            await tx.run(query, need_nmids=need_nmids)


        async with neo4j.AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                await session.write_transaction(clear_cards, query, need_nmids)

        return

    async def clear_keywords_in_neo4j(self, need_keywords: list[str]):
        query = """
        CALL apoc.periodic.iterate(
            "MATCH (keyword:KeywordPhrase) WHERE NOT keyword.text IN $need_keywords RETURN keyword",
            "DETACH DELETE keyword",
            {batchSize: 100, params: {need_keywords: $need_keywords}}
        )
        """

        async def clear_keywords(tx, query, need_keywords):
            await tx.run(query, need_keywords=need_keywords)

        async with neo4j.AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                await session.write_transaction(clear_keywords, query, need_keywords)
        return

    async def clear_dead_nodes(self):
        query = """
        MATCH (n) WHERE NOT EXISTS ((n)--(:KeywordPhrase))
        AND NOT EXISTS ((n)--(:Item))
        DETACH DELETE n 
        """
        async def clear_dead_nodes(tx, query):
            await tx.run(query)

        async with neo4j.AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                await session.write_transaction(clear_dead_nodes, query)

    async def get_keywords_vectors_by_keywords(self, keywords: list[str]):
        query = """
        MATCH (k:KeywordPhrase) WHERE k.text IN $keywords
        RETURN k.text as keyword, k.fastrp as vector
        """

        async def get_keywords_vectors_by_keywords(tx, query, keywords):
            result = await tx.run(query, keywords=keywords)
            records = await result.data()
            data = []
            for record in records:
                vector = record['vector']
                keyword = record['keyword']
                if vector:
                    data.append((keyword, vector))
            return data

        async with neo4j.AsyncGraphDatabase.driver(self.__uri, auth=self.__auth) as driver:
            async with driver.session() as session:
                data = await session.read_transaction(get_keywords_vectors_by_keywords, query, keywords)

        return data

