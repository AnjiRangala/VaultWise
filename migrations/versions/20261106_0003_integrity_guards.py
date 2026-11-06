"""add financial integrity constraints and append-only guards

Revision ID: 20261106_0003
Revises: 20261106_0002
Create Date: 2026-11-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261106_0003"
down_revision: str | Sequence[str] | None = "20261106_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_accounts_non_negative_balance",
        "accounts",
        "available_balance >= 0",
    )
    op.create_check_constraint(
        "ck_accounts_non_negative_overdraft",
        "accounts",
        "overdraft_limit >= 0",
    )
    op.create_check_constraint(
        "ck_financial_transactions_positive_amount",
        "financial_transactions",
        "amount > 0",
    )
    op.create_check_constraint(
        "ck_ledger_entries_positive_amount",
        "ledger_entries",
        "amount > 0",
    )
    op.create_check_constraint(
        "ck_ledger_entries_side",
        "ledger_entries",
        "debit_or_credit IN ('debit', 'credit')",
    )
    op.add_column(
        "audit_events",
        sa.Column(
            "financial_transaction_id",
            sa.String(36),
            sa.ForeignKey("financial_transactions.id"),
            nullable=True,
        ),
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_ledger_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'financial history is append-only';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER ledger_entries_no_update_delete
        BEFORE UPDATE OR DELETE ON ledger_entries
        FOR EACH ROW EXECUTE FUNCTION prevent_ledger_mutation();
        CREATE TRIGGER audit_events_no_update_delete
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION prevent_ledger_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS ledger_entries_no_update_delete ON ledger_entries;
        DROP TRIGGER IF EXISTS audit_events_no_update_delete ON audit_events;
        DROP FUNCTION IF EXISTS prevent_ledger_mutation();
        """
    )
    op.drop_column("audit_events", "financial_transaction_id")
    op.drop_constraint("ck_ledger_entries_side", "ledger_entries", type_="check")
    op.drop_constraint("ck_ledger_entries_positive_amount", "ledger_entries", type_="check")
    op.drop_constraint(
        "ck_financial_transactions_positive_amount",
        "financial_transactions",
        type_="check",
    )
    op.drop_constraint("ck_accounts_non_negative_overdraft", "accounts", type_="check")
    op.drop_constraint("ck_accounts_non_negative_balance", "accounts", type_="check")
