__all__ = ["BaseNeo4jManager"]

import logging
from abc import ABC

from dependency_injector.wiring import inject, Provide
from neo4j import AsyncDriver

from app import AppContainer

logger = logging.getLogger(__name__)


class BaseNeo4jManager(ABC):
    @inject
    def __init__(
        self, neo4j_driver: AsyncDriver = Provide[AppContainer.neo4j_driver]
    ) -> None:
        self.neo4j_driver = neo4j_driver
