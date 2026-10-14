"""add explicit reporting status for profile balances

Revision ID: b4f7c2d91a60
Revises: a81d9f43c201
Create Date: 2026-10-13

Existing numeric values are preserved. Adding each NOT NULL column with a
false server default marks every existing balance as unconfirmed and gives
new rows a safe unconfirmed default.

Downgrade removes the reporting flags and therefore loses all confirmation
state. Export/review those flags and avoid downgrade after users have begun
confirming balances unless the application is being rolled back to code that
does not rely on the provenance state.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4f7c2d91a60"
down_revision: Union[str, Sequence[str], None] = "a81d9f43c201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BALANCE_REPORTING_COLUMNS = (
    "total_savings_reported",
    "emergency_fund_reported",
    "investments_reported",
    "total_debt_reported",
)


def upgrade() -> None:
    for column_name in BALANCE_REPORTING_COLUMNS:
        op.add_column(
            "financial_profiles",
            sa.Column(
                column_name,
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    for column_name in reversed(BALANCE_REPORTING_COLUMNS):
        op.drop_column("financial_profiles", column_name)
