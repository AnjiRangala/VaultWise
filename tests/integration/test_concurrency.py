from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, FinancialTransaction, User
from app.transactions import post_withdrawal


def test_concurrent_withdrawals_allow_only_one_success(
    postgres_engine,
    seeded_account,
) -> None:
    user, account = seeded_account

    def withdraw(amount: str, key: str) -> str:
        with Session(postgres_engine) as session:
            locked_account = session.scalar(select(Account).where(Account.id == account.id))
            actor = session.get(User, user.id)
            try:
                post_withdrawal(session, actor, locked_account, Decimal(amount), key)
            except HTTPException as exc:
                return f"rejected:{exc.status_code}"
            return "posted"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda item: withdraw(*item),
                [("700.00", "withdraw-a"), ("600.00", "withdraw-b")],
            )
        )

    assert sorted(results) == ["posted", "rejected:422"]
    with Session(postgres_engine) as session:
        refreshed = session.get(Account, account.id)
        assert refreshed.available_balance in {
            Decimal("300.0000"),
            Decimal("400.0000"),
        }
        assert (
            session.scalar(
                select(FinancialTransaction.id).where(FinancialTransaction.actor_id == user.id)
            )
            is not None
        )
