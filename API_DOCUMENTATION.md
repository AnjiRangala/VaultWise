# Balance Vault API

All protected endpoints use:

```text
Authorization: Bearer <JWT>
```

Every response includes `X-Request-ID`. A client-provided value is preserved;
otherwise the server generates one. The value is stored on financial audit
events.

Money values are decimal strings in responses and decimal-compatible JSON
values in requests. Money-moving endpoints require:

```text
Idempotency-Key: <actor-scoped-key>
```

## Authentication

### `GET /health`

Returns process liveness without requiring PostgreSQL.

### `GET /health/ready`

Checks PostgreSQL connectivity and returns `{"status":"ready"}` only when the
database is reachable. This endpoint is intended for container readiness
probes.

### `POST /auth/register`

Creates an Account Holder. Request:

```json
{"email":"holder@example.com","password":"a-password-at-least-12"}
```

Returns `201` with the public user profile. Public registration cannot create
Administrator or Auditor users.

### `POST /auth/login`

Request:

```json
{"email":"holder@example.com","password":"a-password-at-least-12"}
```

Returns `200` with `access_token` and `token_type`.

### `GET /auth/me`

Returns the authenticated profile. Requires authentication.

## Accounts

### `POST /accounts`

Creates an active account owned by the authenticated Account Holder.

```json
{"currency":"INR"}
```

Returns `201`. Requires Account Holder or Administrator authorization.

### `GET /accounts`

Returns only accounts owned by the authenticated user.

### `GET /accounts/{account_id}`

Returns one owned account. An inaccessible account returns `404` without
revealing whether another user owns it.

### `GET /accounts/{account_id}/balance`

Returns the current projected balance for an owned account. The response uses
the same decimal representation as the account detail endpoint.

### `GET /accounts/{account_id}/statement`

Returns chronologically ordered posted and refused audit entries for the owned
account. Each item includes transaction ID when a successful posting exists,
action, amount, result, reason, resulting balance, and timestamp.

### `GET /accounts/{account_id}/reconciliation`

Compares the account projection with the balance derived from customer ledger
entries and returns both values plus a `reconciled` boolean.

## Money movement

### `POST /transactions/deposit`

Request:

```json
{"account_id":"<account-id>","amount":"100.00"}
```

Creates a clearing-to-customer double-entry journal and increases the account
projection atomically.

### `POST /transactions/withdraw`

Request:

```json
{"account_id":"<account-id>","amount":"25.00"}
```

Locks the account, checks the available balance, then posts a
customer-to-clearing journal. Insufficient funds create a refused audit event
and no ledger posting.

### `POST /transactions/transfer`

Request:

```json
{
  "source_account_id":"<source-id>",
  "destination_account_id":"<destination-id>",
  "amount":"25.00"
}
```

Locks both accounts in deterministic ID order, verifies currency and status,
then posts one balanced transfer journal.

### `GET /transactions/{transaction_id}`

Returns a transaction created by the authenticated actor. Other actors receive
`404`.

### `GET /transactions?limit=50&offset=0`

Lists only transactions initiated by the authenticated actor. `limit` is
bounded from 1 through 100 and results use stable creation-time plus ID
ordering. The response includes `has_more`.

## Administrative and audit review

- `GET /admin/users` requires the Administrator role.
- `GET /admin/accounts` requires Administrator or Auditor role.
- `GET /audit/events` requires Administrator or Auditor role.

These endpoints are read-only. No administrative balance adjustment endpoint is
exposed until a compensating-entry workflow and approval controls are
implemented.

## Idempotency behavior

The same actor, key, and canonical payload produce one financial effect.
Completed retries return the stored result with `"replayed": true`; the
original response contains `"replayed": false`. Reusing the key with a
different payload returns `409`. Idempotency records are stored in the same
transaction as successful financial effects.
