import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import (
    Account,
    User,
)


@pytest.fixture(scope="session")
def postgres_engine() -> Iterator[Engine]:
    url = os.getenv("LEDGERLINE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set LEDGERLINE_TEST_DATABASE_URL to run PostgreSQL integration tests")

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        engine.dispose()
        pytest.skip(f"PostgreSQL is unavailable: {exc}")

    yield engine
    engine.dispose()


@pytest.fixture
def database_session(postgres_engine: Engine) -> Iterator[Session]:
    session = Session(postgres_engine)
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def seeded_account(database_session: Session) -> tuple[User, Account]:
    user = User(
        id=str(uuid4()),
        email=f"{uuid4().hex}@example.com",
        password_hash="test-only",
        role="account_holder",
    )
    account = Account(
        id=str(uuid4()),
        owner_user_id=user.id,
        account_number=f"TEST-{uuid4().hex[:20]}",
        currency="INR",
        available_balance=1000,
        overdraft_limit=0,
    )
    database_session.add_all([user, account])
    database_session.commit()
    # Use a disposable database: append-only triggers prohibit destructive
    # cleanup of posted financial and audit history.
    yield user, account
