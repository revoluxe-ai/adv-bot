"""Create indexes

Revision ID: c47c97967bdc
Revises: bf00375c155f
Create Date: 2025-03-28 15:56:37.531703

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c47c97967bdc'
down_revision: Union[str, None] = 'bf00375c155f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Индексы для таблицы User
    op.create_index('ix_user_username', 'user', ['username'], unique=False)
    
    # Индексы для таблицы RefLink
    op.create_index('ix_reflink_name', 'reflink', ['name'], unique=False)
    op.create_index('ix_reflink_referrer_id', 'reflink', ['referrer_id'], unique=False)
    op.create_index('ix_reflink_created_at', 'reflink', ['created_at'], unique=False)
    
    # Индексы для таблицы WBUserCabinet
    op.create_index('ix_wbusercabinet_user_id', 'wbusercabinet', ['user_id'], unique=False)
    
    # Индексы для таблицы Payment
    op.create_index('ix_payment_user_id', 'payment', ['user_id'], unique=False)
    
    # Индексы для таблицы WBToken
    op.create_index('ix_wbtoken_user_id', 'wbtoken', ['user_id'], unique=False)


def downgrade() -> None:
    # Удаление индексов для таблицы User
    op.drop_index('ix_user_username', table_name='user')
    
    # Удаление индексов для таблицы RefLink
    op.drop_index('ix_reflink_name', table_name='reflink')
    op.drop_index('ix_reflink_referrer_id', table_name='reflink')
    op.drop_index('ix_reflink_created_at', table_name='reflink')
    
    # Удаление индексов для таблицы WBUserCabinet
    op.drop_index('ix_wbusercabinet_user_id', table_name='wbusercabinet')
    
    # Удаление индексов для таблицы Payment
    op.drop_index('ix_payment_user_id', table_name='payment')
    
    # Удаление индексов для таблицы WBToken
    op.drop_index('ix_wbtoken_user_id', table_name='wbtoken')
