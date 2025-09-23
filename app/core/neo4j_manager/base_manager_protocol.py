from typing import Protocol

from neo4j import AsyncDriver


class BaseManagerProtocol(Protocol):
    neo4j_driver: AsyncDriver = ...
