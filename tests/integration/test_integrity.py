from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Account,
    AuditEvent,
    FinancialTransaction,
    LedgerEntry,
    LedgerTransaction,
    User,
)
from app.transactions import post_deposit


def test_database_rejects_negative_balance(postgres_engine, seeded_account) -> None:
    _, account = seeded_account

    with Session(postgres_engine) as session:
        target = session.get(Account, account.id)
        target.available_balance = Decimal("-0.01")
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_posted_audit_event_cannot_be_deleted(postgres_engine, seeded_account) -> None:
    user, account = seeded_account
    with Session(postgres_engine) as session:
        event = AuditEvent(
            id=str(uuid4()),
            actor_id=user.id,
            action="test",
            account_id=account.id,
            attempted_amount=Decimal("1.00"),
            result="posted",
            resulting_balance=account.available_balance,
            request_id=str(uuid4()),
        )
        session.add(event)
        session.commit()
        event_id = event.id

    with Session(postgres_engine) as session:
        with pytest.raises(Exception, match="financial history is append-only"):
            session.execute(delete(AuditEvent).where(AuditEvent.id == event_id))
            session.commit()
        session.rollback()

        assert session.scalar(select(AuditEvent.id).where(AuditEvent.id == event_id)) == event_id


def test_transaction_rollback_leaves_no_account_change(postgres_engine, seeded_account) -> None:
    _, account = seeded_account
    with Session(postgres_engine) as session:
        target = session.get(Account, account.id)
        target.available_balance = target.available_balance + Decimal("25.00")
        session.flush()
        session.rollback()

    with Session(postgres_engine) as session:
        target = session.get(Account, account.id)
        assert target.available_balance == Decimal("1000.0000")
        assert (
            session.scalar(
                text("SELECT COUNT(*) FROM financial_transactions WHERE source_account_id = :id"),
                {"id": account.id},
            )
            == 0
        )


def test_posted_ledger_entry_cannot_be_updated_or_deleted(
    postgres_engine,
    seeded_account,
) -> None:
    user, account = seeded_account
    with Session(postgres_engine) as session:
        actor = session.get(User, user.id)
        current = session.get(Account, account.id)
        post_deposit(session, actor, current, Decimal("5.00"), "ledger-immutability")
        entry = session.scalar(
            select(LedgerEntry)
            .join(LedgerTransaction, LedgerEntry.ledger_transaction_id == LedgerTransaction.id)
            .join(
                FinancialTransaction,
                LedgerTransaction.financial_transaction_id == FinancialTransaction.id,
            )
            .where(FinancialTransaction.actor_id == user.id)
        )
        entry_id = entry.id

    with Session(postgres_engine) as session:
        entry = session.get(LedgerEntry, entry_id)
        entry.amount = Decimal("999.00")
        with pytest.raises(Exception, match="financial history is append-only"):
            session.commit()
        session.rollback()

        with pytest.raises(Exception, match="financial history is append-only"):
            session.execute(delete(LedgerEntry).where(LedgerEntry.id == entry_id))
            session.commit()
        session.rollback()

        assert session.get(LedgerEntry, entry_id).amount == Decimal("5.0000")
