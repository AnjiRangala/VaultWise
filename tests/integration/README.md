# PostgreSQL integration tests

These tests intentionally require a disposable PostgreSQL database. SQLite is not a substitute for
row locks, transaction isolation, deferred database behavior, or PostgreSQL
triggers.

Financial and audit rows are intentionally retained because append-only
triggers prohibit destructive cleanup of posted history.

Start the development database and apply migrations:

```powershell
docker compose up -d db
$env:VAULTWISE_TEST_DATABASE_URL = $env:DATABASE_URL
alembic upgrade head
pytest tests/integration -q
```

The tests skip with an explicit reason when
`VAULTWISE_TEST_DATABASE_URL` is unset or unreachable. This keeps the normal
unit suite usable without silently pretending that PostgreSQL behavior was
verified.

The next integration-test additions should use separate SQLAlchemy sessions
and synchronization barriers for:

1. Competing withdrawals.
2. Concurrent duplicate idempotency keys.
3. Opposite-direction transfers.
4. Failure injection before commit.
5. Ledger UPDATE and DELETE attempts.
6. Opposite-direction transfers to verify deterministic lock ordering.
