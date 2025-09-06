from neo4j import AsyncNeo4jDriver

from app.core.DI import AppContainer

class Neo4jManager:
    def __init__(self):
        container = AppContainer()
        self._neo4j_driver: AsyncNeo4jDriver = container.databases.container.neo4j_driver()



    async def get_keywords_vectors(self, texts: list[str]) -> dict[str, list[float]]:
        query = """MATCH (k:KeywordPhrase)
        WHERE k.fastrp IS NOT NULL
        AND k.text IN $need
        RETURN k.text as keyword, k.fastrp as vector"""

        async with self._neo4j_driver() as session:
            session




