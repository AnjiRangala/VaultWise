# LedgerLine

LedgerLine is a secure money-movement backend designed around financial integrity,
double-entry accounting, authorization, idempotency, and PostgreSQL concurrency
controls.

The project is being built incrementally as a modular monolith. The current
implementation provides the FastAPI application, typed configuration,
SQLAlchemy database wiring, Alembic migration support, Docker Compose
development services, registration/login with Argon2id and JWT authentication,
role-aware authorization, account ownership, protected account endpoints, and
the first atomic double-entry money movement services.

## Technology

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL 17
- Alembic
- Pytest
- Ruff

PostgreSQL is intentional: SQLite cannot provide a reliable substitute for the
row-level locking and transaction behavior required by later concurrency tests.
Money values will use PostgreSQL `NUMERIC`, never binary floating point.

## Local setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and replace development secrets where appropriate.
Do not commit `.env`.

Start PostgreSQL:

```powershell
docker compose up -d db
```

The Compose API service has a liveness health check. Migrations remain an
explicit operator step so schema changes are visible and reviewable:

```powershell
docker compose up -d api
docker compose ps
```

The API image runs as a non-root user. Apply migrations before starting the API;
the container intentionally does not mutate the database schema automatically.

Run migrations and start the API:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

The API is available at <http://127.0.0.1:8000>. The initial health check is
<http://127.0.0.1:8000/health>, and FastAPI's development documentation is at
<http://127.0.0.1:8000/docs>.

## Web dashboard

LedgerLine includes a React + TypeScript dashboard in `frontend/`. Start the
API first, then open a second PowerShell window:

```powershell
cd "C:\Users\khaja vali\OneDrive\MyProjects\LedgerLine\frontend"
npm install
npm run dev
```

Open <http://localhost:5173>. The dashboard uses the same registration, login,
account, statement, and money-movement APIs as Swagger. It generates a fresh
idempotency key for every deposit, withdrawal, and transfer.

`GET /health/ready` checks PostgreSQL connectivity and returns `503` through
FastAPI's standard database exception handling when the database is
unavailable. Use `/health` for process liveness and `/health/ready` for a
deployment readiness probe.

Every response includes an `X-Request-ID` header. Clients may supply a valid
request ID; otherwise the API generates one. Money-movement audit events use
the same value for traceability.

Run tests and lint:

```powershell
pytest
ruff check .
```

Run static type checking and dependency consistency checks:

```powershell
mypy
python -m pip check
```

The CI workflow runs these checks before the PostgreSQL integration suite.

CI runs the unit suite and PostgreSQL integration checks against PostgreSQL 17
after applying all Alembic migrations. The workflow is in
`.github/workflows/ci.yml`.

PostgreSQL integration checks are separate and require a running database:

```powershell
$env:LEDGERLINE_TEST_DATABASE_URL = "postgresql+psycopg://ledgerline:ledgerline_dev@localhost:5432/ledgerline"
pytest tests/integration -q
```

## Current authentication API

- `POST /auth/register` creates an Account Holder. Passwords must be at least
  12 characters. Public registration cannot create Administrator or Auditor
  accounts.
- `POST /auth/login` accepts a JSON body containing `email` and `password` and
  returns a bearer access token.
- `GET /auth/me` returns the authenticated user.
- `POST /accounts` creates an account for the authenticated Account Holder.
- `GET /accounts` lists only accounts owned by the authenticated user.
- `GET /accounts/{account_id}` returns an owned account. Other users receive a
  safe `404` response rather than account data.
- `GET /accounts/{account_id}/balance` returns the current projected balance
  for an owned account.
- `POST /transactions/deposit` posts an idempotent deposit.
- `POST /transactions/withdraw` posts an idempotent withdrawal after a locked
  balance check.
- `POST /transactions/transfer` posts an idempotent internal transfer using
  deterministic account lock ordering.
- `GET /accounts/{account_id}/statement` returns the account's append-only
  posted and refused audit entries in stable chronological order.
- `GET /accounts/{account_id}/reconciliation` compares the projected balance
  with the customer ledger balance.
- `GET /transactions/{transaction_id}` returns a transaction created by the
  authenticated actor.
- `GET /transactions?limit=50&offset=0` lists the authenticated actor's
  transactions with bounded, stable pagination.
- `GET /admin/users` is Administrator-only.
- `GET /admin/accounts` is available to Administrators and Auditors.
- `GET /audit/events` is available to Administrators and Auditors.

All three money-moving endpoints require an `Idempotency-Key` header. The key
is scoped to the authenticated actor and the canonical request payload is
fingerprinted. Reusing a key with a different payload is rejected. Successful
operations create one financial transaction, one balanced journal, update
account projections, store the replay response, and append an audit event in
one database transaction. A duplicate response includes `replayed: true`.

The migrations create identity, account, financial ledger, idempotency, and
audit tables. The latest migration also adds database-level non-negative and
positive-amount checks plus append-only triggers for ledger and audit history.
Start PostgreSQL before running `alembic upgrade head`; application startup
does not silently fall back to an in-memory database.

Stop local services:

```powershell
docker compose down
```

Use `docker compose down -v` only when intentionally deleting the local
PostgreSQL volume.

## Financial design commitments

All successful money movement will be posted as balanced double-entry journal
entries inside one database transaction. Account projections, idempotency
responses, and audit records must commit atomically with the financial effect.
Posted ledger history will be append-only; reversals will be new compensating
transactions rather than edits.

AI-assisted features, if added, may flag anomalies or summarize audits but will
never independently authorize or post a money movement.
