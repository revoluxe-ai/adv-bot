"""Read-only MCP transport and OAuth bridge for WB Sky.

Модуль монтируется в существующий FastAPI клиентского бота и не является
вторым экспортёром: AI-пакет читается через ``ExportService``. Запись рекламы
и ChangeSet в этот контур не входят. По умолчанию маршруты выключены
(``MCP_ENABLED=false``).
"""
