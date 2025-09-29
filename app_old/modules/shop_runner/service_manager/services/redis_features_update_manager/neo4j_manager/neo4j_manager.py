from app.core.neo4j_manager import BaseNeo4jManager, neo4j_mixins


class Neo4jManager(neo4j_mixins.GetVectorsMixin, BaseNeo4jManager):
    pass
