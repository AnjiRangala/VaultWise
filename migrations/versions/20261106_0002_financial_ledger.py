"""create financial ledger and audit tables

Revision ID: 20261106_0002
Revises: 20261106_0001
Create Date: 2026-11-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261106_0002"
down_revision: str | Sequence[str] | None = "20261106_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "financial_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("transaction_type", sa.String(16), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("source_account_id", sa.String(36), sa.ForeignKey("accounts.id")),
        sa.Column("destination_account_id", sa.String(36), sa.ForeignKey("accounts.id")),
        sa.Column("status", sa.String(16), nullable=False, server_default="posted"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_financial_transactions_actor_id", "financial_transactions", ["actor_id"])
    op.create_table(
        "ledger_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("accounts.id")),
        sa.Column("account_code", sa.String(64), unique=True, nullable=False),
        sa.Column("account_type", sa.String(16), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
    )
    op.create_index("ix_ledger_accounts_account_id", "ledger_accounts", ["account_id"])
    op.create_table(
        "ledger_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "financial_transaction_id",
            sa.String(36),
            sa.ForeignKey("financial_transactions.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("transaction_type", sa.String(16), nullable=False),
        sa.Column(
            "posted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "ledger_transaction_id",
            sa.String(36),
            sa.ForeignKey("ledger_transactions.id"),
            nullable=False,
        ),
        sa.Column(
            "ledger_account_id", sa.String(36), sa.ForeignKey("ledger_accounts.id"), nullable=False
        ),
        sa.Column("debit_or_credit", sa.String(6), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_ledger_entries_ledger_transaction_id", "ledger_entries", ["ledger_transaction_id"]
    )
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="processing"),
        sa.Column("response_body", sa.Text()),
        sa.Column("response_status", sa.Integer()),
        sa.Column(
            "financial_transaction_id", sa.String(36), sa.ForeignKey("financial_transactions.id")
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("actor_id", "idempotency_key"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("accounts.id")),
        sa.Column("attempted_amount", sa.Numeric(19, 4)),
        sa.Column("reason", sa.String(255)),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("resulting_balance", sa.Numeric(19, 4)),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(255)),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("idempotency_records")
    op.drop_index("ix_ledger_entries_ledger_transaction_id", table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_table("ledger_transactions")
    op.drop_index("ix_ledger_accounts_account_id", table_name="ledger_accounts")
    op.drop_table("ledger_accounts")
    op.drop_index("ix_financial_transactions_actor_id", table_name="financial_transactions")
    op.drop_table("financial_transactions")
