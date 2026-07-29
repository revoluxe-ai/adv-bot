"""Live Alembic upgrade/downgrade для epoch migration на disposable PG.

Статические ORM/migration unit-тесты остаются в
``tests/unit/.../test_migration_epoch_alembic_ops.py``.
"""

from __future__ import annotations

import pytest

from tests.integration.card_ab_hold._live_pg_bootstrap import (
    assert_epoch_columns_present,
    create_pre_epoch_advsetting_schema,
    disposable_ab_hold_schema,
    run_epoch_migration_upgrade_downgrade,
)
from tests.support.destructive_pg_dsn import require_validated_live_pg_dsn_or_skip

_EPOCH_COLUMNS_COUNT = 11


@pytest.mark.destructive_local
def test_live_alembic_upgrade_downgrade_epoch_revision() -> None:
    """Live disposable PG: upgrade/downgrade ``d0e1f2a3b4c5`` via Operations.

    При установленном, но невалидном ``TEST_DATABASE_URL`` — fail-closed error,
    не silent skip.
    """
    db_url = require_validated_live_pg_dsn_or_skip()
    with disposable_ab_hold_schema(db_url):
        create_pre_epoch_advsetting_schema(db_url)
        run_epoch_migration_upgrade_downgrade(db_url)
        present = assert_epoch_columns_present(db_url)
        assert len(present) == _EPOCH_COLUMNS_COUNT
