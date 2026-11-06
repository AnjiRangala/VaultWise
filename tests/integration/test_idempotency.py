from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Account, FinancialTransaction, User
from app.transactions import post_deposit


def test_repeated_idempotent_deposit_has_one_financial_effect(
    postgres_engine,
    seeded_account,
) -> None:
    user, account = seeded_account
    with Session(postgres_engine) as session:
        current = session.get(Account, account.id)
        actor = session.get(User, user.id)
        first = post_deposit(session, actor, current, Decimal("50.00"), "same-deposit-key")

    with Session(postgres_engine) as session:
        current = session.get(Account, account.id)
        actor = session.get(User, user.id)
        second = post_deposit(session, actor, current, Decimal("50.00"), "same-deposit-key")
        assert second == {**first, "replayed": True}
        assert current.available_balance == Decimal("1050.0000")
        count = session.scalar(
            select(func.count(FinancialTransaction.id)).where(
                FinancialTransaction.actor_id == user.id
            )
        )
        assert count == 1


def test_same_key_with_changed_amount_is_rejected(postgres_engine, seeded_account) -> None:
    user, account = seeded_account
    with Session(postgres_engine) as session:
        current = session.get(Account, account.id)
        actor = session.get(User, user.id)
        post_deposit(session, actor, current, Decimal("10.00"), "conflicting-key")

    with Session(postgres_engine) as session:
        current = session.get(Account, account.id)
        actor = session.get(User, user.id)
        try:
            post_deposit(session, actor, current, Decimal("11.00"), "conflicting-key")
        except HTTPException as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("Changed idempotency payload was accepted")
