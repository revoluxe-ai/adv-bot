__all__ = ["GetVectorsMixin"]

from neo4j import AsyncSession

from ..neo4j_session_decorator import neo4j_session


class GetVectorsMixin:
    @neo4j_session
    async def get_keywords_vectors(
        self, texts: list[str], *, session: AsyncSession
    ) -> dict[str, list[float]]:
        async def _get_keywords_vectors_tx(tx) -> dict[str, list[float]]:
            query = """
            MATCH (k:KeywordPhrase)
            WHERE k.fastrp IS NOT NULL
            AND k.text IN $texts
            RETURN k.text AS text, k.fastrp AS vector
            """
            result = await tx.run(query, {"texts": texts})
            records = await result.data()
            return {record["text"]: record["vector"] for record in records}

        result = await session.execute_read(_get_keywords_vectors_tx)
        return result

    @neo4j_session
    async def get_items_vectors(
        self, nmids: set[int], *, session: AsyncSession
    ) -> dict[int, list[float]]:
        async def _get_items_vectors_tx(tx) -> dict[int, list[float]]:  # ignore
            query = """
            MATCH (i:Item)
            WHERE i.fastrp IS NOT NULL
            AND i.nmid IN $nmids
            RETURN i.nmid AS nmid, i.fastrp AS vector
            """
            result = await tx.run(query, {"nmids": list(nmids)})
            records = await result.data()
            return {record["nmid"]: record["vector"] for record in records}

        result = await session.execute_read(_get_items_vectors_tx)
        return result
