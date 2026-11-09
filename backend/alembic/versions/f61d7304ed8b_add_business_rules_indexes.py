"""add_business_rules_indexes

Revision ID: f61d7304ed8b
Revises: c99320d8eb8b
Create Date: 2026-11-09 13:55:31.700771

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f61d7304ed8b'
down_revision: Union[str, Sequence[str], None] = 'c99320d8eb8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1. Если в income_entries или expense_entries нет deleted_at, добавляем
    income_cols = [c['name'] for c in insp.get_columns('income_entries')]
    if 'deleted_at' not in income_cols:
        op.add_column('income_entries', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    expense_cols = [c['name'] for c in insp.get_columns('expense_entries')]
    if 'deleted_at' not in expense_cols:
        op.add_column('expense_entries', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    # 2. Заменяем обычный индекс на clients.phone индексом с text_pattern_ops
    op.drop_index('ix_clients_phone', table_name='clients')
    op.create_index(
        'ix_clients_phone',
        'clients',
        ['phone'],
        unique=False,
        postgresql_ops={'phone': 'text_pattern_ops'},
    )

    # 3. Добавляем новые индексы
    op.create_index('ix_appointments_status_starts_at', 'appointments', ['status', 'starts_at'], unique=False)
    op.create_index('ix_expense_entries_occurred_on', 'expense_entries', ['occurred_on'], unique=False)
    op.create_index('ix_income_entries_occurred_on', 'income_entries', ['occurred_on'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем добавленные индексы
    op.drop_index('ix_income_entries_occurred_on', table_name='income_entries')
    op.drop_index('ix_expense_entries_occurred_on', table_name='expense_entries')
    op.drop_index('ix_appointments_status_starts_at', table_name='appointments')

    # Возвращаем обычный индекс на clients.phone
    op.drop_index('ix_clients_phone', table_name='clients')
    op.create_index('ix_clients_phone', 'clients', ['phone'], unique=False)
