"""settings_singleton_check

Revision ID: e2a4b6c8d0e1
Revises: f61d7304ed8b
Create Date: 2026-11-10 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e2a4b6c8d0e1'
down_revision: Union[str, Sequence[str], None] = 'f61d7304ed8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Удаляем лишние строки, оставляя запись с минимальным id
    op.execute(
        sa.text(
            "DELETE FROM settings WHERE id NOT IN (SELECT min(id) FROM settings)"
        )
    )
    # 2. Если оставшаяся запись имеет id != 1, переносим её на id = 1
    op.execute(
        sa.text(
            "UPDATE settings SET id = 1 WHERE id != 1"
        )
    )
    # 3. Добавляем CHECK (id = 1)
    op.create_check_constraint(
        "chk_settings_singleton_id",
        "settings",
        "id = 1",
    )


def downgrade() -> None:
    op.drop_constraint("chk_settings_singleton_id", "settings", type_="check")
