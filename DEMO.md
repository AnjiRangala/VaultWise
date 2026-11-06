# LedgerLine five-minute demo

This demo is intended for a local development environment only. It must not be
run against real money or production users.

## 1. Start the database and application

```powershell
docker compose up -d db
alembic upgrade head
uvicorn app.main:app --reload
```

For the containerized API, run `docker compose up -d api` after applying the
migrations and verify `docker compose ps` reports the API as healthy.

The image runs as a non-root user and expects the database schema to have been
migrated before startup.

## 2. Register and log in

Use the Swagger UI at <http://127.0.0.1:8000/docs>:

1. `POST /auth/register` with a 12-character-or-longer password.
2. `POST /auth/login`.
3. Authorize Swagger with the returned bearer token.

## 3. Create and fund an account

1. Call `POST /accounts` with `{"currency":"INR"}`.
2. Call `POST /transactions/deposit` with an `Idempotency-Key` and
   `{"account_id":"...","amount":"1000.00"}`.
3. Repeat the same request with the same key and show that the financial
   operation is not duplicated.

## 4. Demonstrate rejection and transfer

1. Withdraw `1200.00` and show the insufficient-funds response.
2. Call the statement endpoint and show the refused audit entry.
3. Create a second account.
4. Transfer `250.00` between the accounts with a fresh idempotency key.
5. Retrieve the transaction and both statements.

## 5. Explain the financial guarantees

- Amounts use decimal values, not binary floating point.
- Successful operations create balanced debit and credit entries.
- Idempotency keys prevent duplicate observable financial effects.
- Source and destination accounts are locked in deterministic order.
- Ledger and audit history are protected by PostgreSQL append-only triggers.

Do not claim concurrency protection has been demonstrated until the PostgreSQL
integration tests have run successfully.
