from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, User
from app.transactions import post_transfer


def test_opposite_direction_transfers_use_consistent_lock_order(
    postgres_engine,
    seeded_account,
) -> None:
    user, first = seeded_account
    with Session(postgres_engine) as session:
        second = Account(
            id=str(uuid4()),
            owner_user_id=user.id,
            account_number=f"TEST-{uuid4().hex[:20]}",
            currency="INR",
            available_balance=Decimal("1000.00"),
            overdraft_limit=0,
        )
        session.add(second)
        session.commit()
        second_id = second.id

    def transfer(source_id: str, destination_id: str, key: str) -> str:
        with Session(postgres_engine) as session:
            actor = session.get(User, user.id)
            source = session.scalar(select(Account).where(Account.id == source_id))
            destination = session.scalar(select(Account).where(Account.id == destination_id))
            try:
                post_transfer(session, actor, source, destination, Decimal("10.00"), key)
            except HTTPException as exc:
                return f"rejected:{exc.status_code}"
            return "posted"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda item: transfer(*item),
                [
                    (first.id, second_id, "direction-a"),
                    (second_id, first.id, "direction-b"),
                ],
            )
        )

    assert sorted(results) == ["posted", "posted"]
