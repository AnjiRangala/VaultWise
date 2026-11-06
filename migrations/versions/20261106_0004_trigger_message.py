"""clarify append-only trigger message

Revision ID: 20261106_0004
Revises: 20261106_0003
Create Date: 2026-11-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261106_0004"
down_revision: str | Sequence[str] | None = "20261106_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_ledger_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'financial history is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_ledger_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'posted ledger entries are append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
