from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Account, FinancialTransaction, LedgerEntry, User
from app.transactions import post_deposit, post_transfer


def test_transfer_conserves_customer_balances(postgres_engine, seeded_account) -> None:
    user, source = seeded_account
    with Session(postgres_engine) as session:
        destination = Account(
            id=str(uuid4()),
            owner_user_id=user.id,
            account_number=f"TEST-{uuid4().hex[:20]}",
            currency="INR",
            available_balance=Decimal("100.00"),
            overdraft_limit=0,
        )
        session.add(destination)
        session.commit()
        destination_id = destination.id

    with Session(postgres_engine) as session:
        actor = session.get(User, user.id)
        source_account = session.get(Account, source.id)
        post_deposit(session, actor, source_account, Decimal("50.00"), "fund-source")

    with Session(postgres_engine) as session:
        actor = session.get(User, user.id)
        source_account = session.get(Account, source.id)
        destination_account = session.get(Account, destination_id)
        post_transfer(
            session,
            actor,
            source_account,
            destination_account,
            Decimal("25.00"),
            "transfer-key",
        )

    with Session(postgres_engine) as session:
        refreshed_source = session.get(Account, source.id)
        refreshed_destination = session.get(Account, destination_id)
        assert (
            refreshed_source.available_balance + refreshed_destination.available_balance
            == Decimal("1150.0000")
        )
        ledger_entry_count = session.scalar(select(func.count(LedgerEntry.id)))
        transaction_count = session.scalar(select(func.count(FinancialTransaction.id)))
        assert ledger_entry_count == transaction_count * 2
