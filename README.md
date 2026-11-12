# Balance Vault — Secure Money Movement System

## 1. Project introduction

Balance Vault is a secure financial application for reliable money movement. It
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
BalanceVault/
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
cd "C:\path\to\BalanceVault"
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
APP_NAME=Balance Vault
APP_ENV=development
DATABASE_URL=postgresql+psycopg://ledgerline:replace-with-a-unique-local-password@localhost:5432/ledgerline
POSTGRES_PASSWORD=replace-with-the-same-url-safe-local-password
JWT_SECRET_KEY=replace-with-a-unique-local-secret-of-at-least-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
```

Replace the placeholders before starting the application. Use a unique local
database password and signing key; do not reuse production credentials. The
Compose API container derives its internal database URL from
`POSTGRES_PASSWORD`, while a locally run API uses `DATABASE_URL`.

For production, configure `DATABASE_URL` and a unique `JWT_SECRET_KEY` of at
least 32 characters through the deployment platform's secret manager.
Standard `postgresql://` and `postgres://` URLs are adapted to the installed
psycopg 3 driver automatically.

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
$body = '{"email":"demo@example.com","password":"<choose-a-password-of-at-least-12-characters>"}'
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
Password: <choose-a-password-of-at-least-12-characters>
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

The API container runs as a non-root user. For a hosted deployment, use:

```text
Managed PostgreSQL → FastAPI Web Service → React Static Site
```

The repository includes a Render Blueprint in `render.yaml`. Create a
Blueprint from this repository and review the resources before applying it.
It uses a free static site, a free Docker web service, and free PostgreSQL.
The API container runs `alembic upgrade head` before starting Uvicorn; if a
migration fails, the API does not start. Its readiness check also verifies
PostgreSQL connectivity. Render generates the JWT signing key and wires the
database URL, API URL, and CORS origin between services without committing
secrets.

**Free Render resources are for hobby/testing use, not production financial
data.** The API sleeps after 15 minutes without traffic and can take about a
minute to wake. Free web services share a 750-hour monthly allowance per
workspace and can be suspended when usage allowances are exhausted. The free
PostgreSQL database is limited to 1 GB, has no backups, and expires 30 days
after creation. After a further 14-day grace period Render deletes the database
and all its data. Do not store real balances or other irreplaceable data there.
These limits are documented in [Render's free-instance
policy](https://render.com/docs/free) and [static site
docs](https://render.com/docs/static-sites).

For a longer-lived $0 PostgreSQL option, [Neon's Free
plan](https://neon.com/pricing) is permanent and does not require a credit
card. It currently allows up to 100 projects, 1 GB per project, and 20 GB
across projects. To use it, create a Neon PostgreSQL database, set the API
service's `DATABASE_URL` in Render to Neon's connection string (keep it secret;
the application adapts standard PostgreSQL URLs to psycopg 3), and remove or
omit the Render Postgres resource and its `fromDatabase` variable from the
Blueprint. The container startup migration and readiness check work with this
PostgreSQL option as well. Neon is still a free-tier service with quotas;
arrange independent backups and verify its current terms before storing
important data.

For either database choice, verify `/health` and `/health/ready` after deploy.
Do not treat any free-tier setup as a production banking or financial ledger
service.

The current UI and API provide account-holder registration, authentication,
accounts, money movement, statements, and read-only admin/auditor API routes.
There is no admin UI, approval workflow, or public administrator provisioning
flow in this repository; these require product requirements and are not
created by the deployment configuration.

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
$env:BALANCE_VAULT_TEST_DATABASE_URL = `
  $env:DATABASE_URL
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
