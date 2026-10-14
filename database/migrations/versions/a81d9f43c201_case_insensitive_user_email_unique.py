"""enforce case-insensitive user email uniqueness

Revision ID: a81d9f43c201
Revises: 56da330b2b62
Create Date: 2026-10-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a81d9f43c201"
down_revision: Union[str, Sequence[str], None] = "56da330b2b62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This index prevents case-variant duplicate registrations even when
    # registration requests race or bypass the API normalization check.
    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_users_email_lower", table_name="users")
