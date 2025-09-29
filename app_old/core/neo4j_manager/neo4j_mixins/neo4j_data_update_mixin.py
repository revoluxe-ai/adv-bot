__all__ = ["Neo4jDataUpdateMixin"]

import logging

from neo4j import AsyncSession

from ..neo4j_session_decorator import neo4j_session
from ...wb_api.data_classes.namedtuples import KeywordPhrase

logger = logging.getLogger(__name__)


class Neo4jDataUpdateMixin:
    """
    Миксин для обновления данных в Neo4j.
    Содержит методы для upsert товаров и ключевых фраз.
    """

    @neo4j_session
    async def add_keyword_phrase(
        self, phrase_data_list: list[KeywordPhrase], session: AsyncSession
    ):
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

        result = await session.execute_write(
            lambda tx: tx.run(query, parameters={"data_list": data_list})
        )

        return result
