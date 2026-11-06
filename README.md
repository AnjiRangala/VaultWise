# LedgerLine — Secure Money Movement System

## 1. Project introduction

LedgerLine is a secure financial application for reliable money movement. It
provides deposits, withdrawals, transfers, balances, and statements while
protecting financial integrity with JWT authentication, Argon2id password
hashing, role-based authorization, idempotency, deterministic row locking,
double-entry accounting, PostgreSQL constraints, and immutable audit history.

The repository is a modular monolith with a FastAPI backend and a React +
TypeScript web dashboard. Public registration creates Account Holder users.
Administrator and Auditor access must be provisioned through a controlled
administrative process; it is intentionally not exposed through public signup.

## 2. Architecture

```text
Browser
  └── frontend/ (React + TypeScript + Vite)
        └── HTTP/JSON + JWT
              └── app/ (FastAPI modular monolith)
                    ├── routers and schemas
                    ├── authentication and authorization
                    ├── money-movement services
                    └── SQLAlchemy
                          └── PostgreSQL 17
                                └── Alembic migrations
```

### Repository layout

```text
LedgerLine/
├── app/                 # FastAPI backend application
├── frontend/            # React + TypeScript dashboard
├── tests/               # Unit and PostgreSQL integration tests
├── migrations/          # Alembic database migrations
├── README.md
├── THREATS.md
├── PROMPTS.md
├── API_DOCUMENTATION.md
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

### Technology

- Python 3.12+
- FastAPI
- React, TypeScript, and Vite
- SQLAlchemy 2.x
- PostgreSQL 17
- Alembic
- Pytest, Ruff, and MyPy

Money values use Python `Decimal` and PostgreSQL `NUMERIC(19,4)`, never binary
floating point. SQLite is not used for financial concurrency verification.

## 3. Installation

Prerequisites:

- Python 3.12 or newer
- PostgreSQL 17, or Docker Desktop
- Node.js 20 or newer for the dashboard

Create and activate a backend environment:

```powershell
cd "C:\path\to\LedgerLine"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Install frontend dependencies:

```powershell
cd frontend
npm install
cd ..
```

## 4. Environment setup

Create the environment file:

```powershell
Copy-Item .env.example .env
```

Development configuration:

```env
APP_NAME=LedgerLine
APP_ENV=development
DATABASE_URL=postgresql+psycopg://ledgerline:ledgerline_dev@localhost:5432/ledgerline
JWT_SECRET_KEY=replace-this-development-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
```

For production, generate a secret of at least 32 characters:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Never commit `.env`, production secrets, or database credentials.

## 5. Run the application

Start PostgreSQL:

```powershell
docker compose up -d db
```

Apply migrations:

```powershell
alembic upgrade head
```

Start the backend in one terminal:

```powershell
uvicorn app.main:app --reload
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

Open the dashboard at <http://localhost:5173>. The API is available at
<http://127.0.0.1:8000>, Swagger at <http://127.0.0.1:8000/docs>, and liveness
at <http://127.0.0.1:8000/health>. `GET /health/ready` verifies PostgreSQL
connectivity and returns `503` when the database is unavailable.

Stop local services:

```powershell
docker compose down
```

Use `docker compose down -v` only when intentionally deleting local database
data.

## 6. API usage

Protected endpoints require the JWT returned by `POST /auth/login`.

### Register and login

```powershell
$body = '{"email":"demo@example.com","password":"DemoPassword123!"}'
Invoke-RestMethod http://127.0.0.1:8000/auth/register -Method Post `
  -ContentType "application/json" -Body $body

Invoke-RestMethod http://127.0.0.1:8000/auth/login -Method Post `
  -ContentType "application/json" -Body $body
```

### Create an account

```http
POST /accounts
Authorization: Bearer <access-token>
Content-Type: application/json
```

```json
{
  "currency": "INR"
}
```

### Deposit

```http
POST /transactions/deposit
Authorization: Bearer <access-token>
Idempotency-Key: demo-deposit-001
Content-Type: application/json
```

```json
{
  "account_id": "<account-id>",
  "amount": "1000.00"
}
```

Repeating the same request with the same idempotency key returns
`"replayed": true` without duplicating the financial effect.

### Withdrawal and transfer

```json
POST /transactions/withdraw
{
  "account_id": "<account-id>",
  "amount": "250.00"
}
```

```json
POST /transactions/transfer
{
  "source_account_id": "<source-account-id>",
  "destination_account_id": "<destination-account-id>",
  "amount": "100.00"
}
```

Both operations require a unique `Idempotency-Key` header. The complete
endpoint list and response examples are in
[API_DOCUMENTATION.md](./API_DOCUMENTATION.md).

## 7. Seed accounts and credentials

There is no automatic production seed user and no committed administrator or
auditor password. This prevents credentials from being exposed in source
control.

For a local demo, create an Account Holder through the dashboard or
`POST /auth/register`:

```text
Email: demo@example.com
Password: DemoPassword123!
Role: account_holder
```

Public registration cannot create Administrator or Auditor users. Those roles
must be created by an approved operator using a secure provisioning process.
Do not add real credentials to this README, `.env`, or Git history.

## 8. Deployment instructions

The included Docker setup runs PostgreSQL and the API:

```powershell
docker compose up -d db
alembic upgrade head
docker compose up -d api
docker compose ps
```

The API container runs as a non-root user and expects migrations to be applied
explicitly. For a hosted deployment, use:

```text
Managed PostgreSQL → FastAPI Web Service → React Static Site
```

Configure the backend with production `DATABASE_URL`, `APP_ENV=production`,
and a strong `JWT_SECRET_KEY`. Configure the frontend with
`VITE_API_URL=https://<your-api-host>`. Add the deployed frontend origin to
the backend CORS allow-list before serving the site publicly. Verify `/health`
and `/health/ready` after deployment.

## 9. Testing instructions

Run backend tests:

```powershell
pytest -q
```

Run lint, type, and dependency checks:

```powershell
ruff check .
mypy
python -m pip check
```

Run frontend checks:

```powershell
cd frontend
npm test
npm run build
cd ..
```

Run PostgreSQL integration tests:

```powershell
$env:LEDGERLINE_TEST_DATABASE_URL = `
  "postgresql+psycopg://ledgerline:ledgerline_dev@localhost:5432/ledgerline"
pytest tests/integration -q
```

The integration suite verifies concurrent withdrawals, deadlock-safe transfers,
idempotency, balance conservation, rollback behavior, database constraints,
and append-only ledger/audit triggers. CI runs the same checks against
PostgreSQL 17 using [.github/workflows/ci.yml](./.github/workflows/ci.yml).

## Security and financial guarantees

Successful money movements create balanced debit and credit entries, update
account projections, store idempotency responses, and append audit events in
one database transaction. Posted ledger history is append-only; reversals must
be new compensating transactions rather than edits.

Every response includes an `X-Request-ID` for traceability. See
[THREATS.md](./THREATS.md) for the threat inventory and mitigations, and
[PROMPTS.md](./PROMPTS.md) for the AI-assisted engineering log.
