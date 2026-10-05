"""Пакет control plane миграций ClickHouse.

Spec ``clickhouse-migration-lifecycle``: запускатор живёт рядом с корпусом
``scripts/clickhouse_migrations`` и не входит в runtime приложения.
Журнал цели и сессия PostgreSQL — отдельные швы; этот пакет их не открывает
сетевым вызовом.
"""
