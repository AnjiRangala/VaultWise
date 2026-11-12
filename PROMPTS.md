# AI Engineering Log

This log records actual AI-assisted work performed on Balance Vault (formerly
LedgerLine). The workspace
was not a Git repository during these entries, so commit links are explicitly
recorded as unavailable rather than fabricated.

## 2026-11-06 — Initial repository assessment

- **Tool:** Copilot SDK in VS Code
- **Request:** Inspect the complete workspace before implementation and produce
  the architecture, schema, threat model, concurrency scenarios, roadmap, and
  first milestone.
- **Generated:** The assessment identified an empty workspace, no baseline
  tests, a modular-monolith architecture, PostgreSQL requirements, and the
  initial foundation milestone.
- **Verification:** Workspace inspection, `pytest --collect-only -q`, and
  environment checks were run.
- **Change:** No application code was changed during the assessment.
- **Commit:** Unavailable; the directory was not a Git repository.

## 2026-11-06 — Backend foundation

- **Tool:** Copilot SDK in VS Code
- **Request:** Implement the first foundation milestone.
- **Generated:** FastAPI application, typed settings, SQLAlchemy wiring,
  Alembic setup, Docker Compose, environment template, health route, and
  baseline test.
- **Verification:** `pytest`, `ruff check .`, Python compilation, and
  `docker compose config` passed. Docker PostgreSQL startup was attempted but
  Docker Desktop was unavailable.
- **Change:** Added the foundation files and documented the runtime limitation.
- **Commit:** Unavailable; the directory was not a Git repository.

## 2026-11-06 — Authentication and authorization

- **Tool:** Copilot SDK in VS Code
- **Request:** Continue with registration, Argon2id hashing, JWTs, roles,
  ownership authorization, and account endpoints.
- **Generated:** Authentication module, user/account models, schemas, routes,
  identity migration, and authentication tests.
- **Verification:** `pytest` reported 4 passing tests, Ruff passed, and the
  migration head was discovered.
- **Change:** Public registration is restricted to Account Holder users;
  account access is owner-scoped.
- **Commit:** Unavailable; the directory was not a Git repository.

## 2026-11-06 — Atomic money movement

- **Tool:** Copilot SDK in VS Code
- **Request:** Continue without pausing and implement the core financial
  functionality.
- **Generated:** Double-entry ledger models, deposits, withdrawals, transfers,
  actor-scoped idempotency, audit events, statements, and migrations.
- **Verification:** Unit tests, Ruff, Python compilation, route inspection,
  and Compose configuration validation passed.
- **Change:** Money movement requires an idempotency key and uses decimal
  amounts. PostgreSQL runtime concurrency tests remain pending while Docker is
  unavailable.
- **Commit:** Unavailable; the directory was not a Git repository.

## 2026-11-06 — Integrity hardening

- **Tool:** Copilot SDK in VS Code
- **Request:** Continue autonomously with security, immutability,
  reconciliation-related API surfaces, and documentation.
- **Generated:** Database check constraints, append-only PostgreSQL triggers,
  transaction lookup, transaction-linked audit entries, API documentation,
  and threat model.
- **Verification:** `pytest` reported 6 passing tests, Ruff passed, compilation
  passed, and Alembic reported migration `20261106_0003` as the head.
- **Change:** Added database-level protections against negative balances,
  non-positive postings, invalid debit/credit sides, and ledger/audit updates
  or deletes.
- **Commit:** Unavailable; the directory was not a Git repository.

## 2026-11-06 — PostgreSQL behavior verification

- **Tool:** Copilot SDK in VS Code
- **Request:** Continue with executable PostgreSQL checks for concurrency,
  idempotency, rollback, constraints, and append-only behavior.
- **Generated:** Disposable-database integration fixtures, concurrent
  withdrawal tests using separate sessions, duplicate and conflicting
  idempotency tests, negative-balance checks, audit immutability checks, and
  rollback checks.
- **Verification:** The tests collect and skip with explicit reasons when
  `BALANCE_VAULT_TEST_DATABASE_URL` is unavailable. The local unit suite reports
  10 passing tests; PostgreSQL execution is configured in CI.
- **Change:** Added integration test files and CI PostgreSQL execution.
- **Commit:** Unavailable; the directory was not a Git repository.

## 2026-11-06 — Statement and deadlock coverage

- **Tool:** Copilot SDK in VS Code
- **Request:** Continue with stable transaction pagination, transfer
  conservation, and opposing-direction lock-order tests.
- **Generated:** Actor-scoped bounded transaction listing, transfer
  conservation coverage, and concurrent opposite-direction transfer tests.
- **Verification:** Ruff, compilation, and the complete local suite passed;
  PostgreSQL tests remain CI-enabled and explicitly skipped locally without a
  database URL.
- **Change:** Added `/transactions` pagination and lock-order integration
  coverage.
- **Commit:** Unavailable; the directory was not a Git repository.

## 2026-11-06 — Request traceability

- **Tool:** Copilot SDK in VS Code
- **Request:** Continue with end-to-end request traceability for successful and
  refused money movement.
- **Generated:** Request-ID middleware, context propagation, response headers,
  and audit-event correlation.
- **Verification:** Request-ID preservation tests, Ruff, MyPy, compilation,
  and the full local test suite passed.
- **Change:** Added `X-Request-ID` generation/preservation and reused it in
  financial audit records.
- **Commit:** Unavailable; the directory was not a Git repository.
