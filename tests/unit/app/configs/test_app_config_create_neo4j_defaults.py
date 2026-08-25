"""Smoke: AppConfig.create не падает на Neo4jConfig ValidationError в unit.

Root conftest задаёт NEO4J_* через setdefault до app-импортов; этот тест
фиксирует, что фабрика конфигурации собирается с этими defaults.
"""

from __future__ import annotations

import os

import pytest

from app.configs.app_config import AppConfig


@pytest.mark.unit
def test_app_config_create_succeeds_with_neo4j_test_defaults() -> None:
    """AppConfig.create() успешен, когда NEO4J_* заданы тестовыми defaults."""
    for key in ("NEO4J_URI", "NEO4J_NAME", "NEO4J_PASSWORD", "NEO4J_PORT"):
        assert os.environ.get(key), f"ожидался тестовый default для {key}"

    config = AppConfig.create()

    assert config.infrastructure.neo4j.uri
    assert config.infrastructure.neo4j.name
    assert config.infrastructure.neo4j.password
    assert config.infrastructure.neo4j.port > 0
