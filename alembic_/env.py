# alembic_/env.py
import os
from logging.config import fileConfig

import dotenv
from sqlalchemy import engine_from_config, pool
from sqlalchemy.orm import configure_mappers

from alembic import context
from app.admin_bot.sender.utils.db.models import *
from app.modules.common_slaves.wildberries.models import *
from app.modules.token_monitoring.models import *
from app.payments.db.models import *
from app.utils.db.models import *
from app.modules.wb_adv_updater.modules.balance_exp_informer.models import *
from app.modules.billing.event_manager.models import *
from app.modules.rentgen_access.models import *  # noqa: F401
from app.utils.db.base import BaseTable as Base
from app.utils.db.session_maker import get_alchemy_row_for_migration

dotenv.load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Job wrapper may pass DATABASE_URL; otherwise legacy POSTGRES_* settings.
row = get_alchemy_row_for_migration()
config.set_main_option("sqlalchemy.url", row)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = [Base.metadata]
# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

configure_mappers()


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    If Config.attributes['connection'] is set (Job wrapper), reuse that
    Connection and do not create a second Engine. Otherwise create NullPool
    Engine from sqlalchemy.url.
    """
    connection = config.attributes.get("connection")
    if connection is not None:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            # Job wrapper: mark PARTIAL only after Alembic starts applying
            # migrations — not during env.py import/settings/configure.
            on_begin = config.attributes.get("on_migrations_begin")
            if callable(on_begin):
                on_begin()
            context.run_migrations()
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Standalone alembic upgrade: one transaction for the whole run
        # (default). transaction_per_migration is Job-wrapper only.
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            on_begin = config.attributes.get("on_migrations_begin")
            if callable(on_begin):
                on_begin()
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
