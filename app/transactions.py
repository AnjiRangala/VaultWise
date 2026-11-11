import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Account,
    AccountStatus,
    AuditEvent,
    FinancialTransaction,
    IdempotencyRecord,
    LedgerAccount,
    LedgerEntry,
    LedgerTransaction,
    User,
)
from app.request_context import get_request_id


def request_hash(operation: str, payload: dict[str, str]) -> str:
    canonical = json.dumps({"operation": operation, "payload": payload}, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _account_ledger(db: Session, account: Account) -> LedgerAccount:
    ledger = db.scalar(select(LedgerAccount).where(LedgerAccount.account_id == account.id))
    if ledger is None:
        ledger = LedgerAccount(
            account_id=account.id,
            account_code=f"CUSTOMER:{account.account_number}",
            account_type="customer",
            currency=account.currency,
        )
        db.add(ledger)
        db.flush()
    return ledger


def _external_ledger(db: Session, currency: str) -> LedgerAccount:
    code = f"CLEARING:{currency}"
    ledger = db.scalar(select(LedgerAccount).where(LedgerAccount.account_code == code))
    if ledger is None:
        ledger = LedgerAccount(
            account_code=code,
            account_type="clearing",
            currency=currency,
        )
        db.add(ledger)
        db.flush()
    return ledger


def _begin_idempotency(
    db: Session,
    actor_id: str,
    key: str,
    fingerprint: str,
) -> IdempotencyRecord:
    record = db.scalar(
        select(IdempotencyRecord)
        .where(
            IdempotencyRecord.actor_id == actor_id,
            IdempotencyRecord.idempotency_key == key,
        )
        .with_for_update()
    )
    if record is not None:
        if record.request_hash != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key was reused with a different request",
            ) from None
        return record

    record = IdempotencyRecord(
        actor_id=actor_id,
        idempotency_key=key,
        request_hash=fingerprint,
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.actor_id == actor_id,
                IdempotencyRecord.idempotency_key == key,
            )
            .with_for_update()
        )
        if existing is None:
            raise
        if existing.request_hash != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key was reused with a different request",
            ) from None
        return existing
    return record


def _post(
    db: Session,
    actor: User,
    operation: str,
    amount: Decimal,
    currency: str,
    source: Account | None,
    destination: Account | None,
    idempotency_key: str,
    payload: dict[str, str],
) -> dict[str, object]:
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")
    if source is not None and destination is not None and source.id == destination.id:
        raise HTTPException(status_code=422, detail="Source and destination must differ")
    if source is not None and source.owner_user_id != actor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    fingerprint = request_hash(operation, payload)
    record = _begin_idempotency(db, actor.id, idempotency_key, fingerprint)
    if record.status == "completed" and record.response_body is not None:
        replay = json.loads(record.response_body)
        replay["replayed"] = True
        return replay
    if record.status == "failed" and record.response_body is not None:
        raise HTTPException(
            status_code=record.response_status or status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=json.loads(record.response_body)["error"],
        )
    accounts = [account for account in (source, destination) if account is not None]
    accounts.sort(key=lambda account: account.id)
    for account in accounts:
        db.refresh(account, with_for_update=True)
        if account.status != AccountStatus.ACTIVE:
            raise HTTPException(status_code=409, detail="Account is not active")
        if account.currency != currency:
            raise HTTPException(status_code=422, detail="Currency mismatch")
    if source is not None and source.available_balance < amount:
        failure = {"error": "Insufficient funds"}
        record.status = "failed"
        record.response_body = json.dumps(failure)
        record.response_status = status.HTTP_422_UNPROCESSABLE_CONTENT
        record.completed_at = datetime.now(UTC)
        db.add(
            AuditEvent(
                actor_id=actor.id,
                financial_transaction_id=None,
                action=operation,
                account_id=source.id,
                attempted_amount=amount,
                reason="insufficient_funds",
                result="refused",
                resulting_balance=source.available_balance,
                request_id=get_request_id(),
                idempotency_key=idempotency_key,
            )
        )
        db.commit()
        raise HTTPException(status_code=422, detail=failure["error"])

    transaction = FinancialTransaction(
        actor_id=actor.id,
        transaction_type=operation,
        amount=amount,
        currency=currency,
        source_account_id=source.id if source else None,
        destination_account_id=destination.id if destination else None,
    )
    db.add(transaction)
    db.flush()
    journal = LedgerTransaction(
        financial_transaction_id=transaction.id,
        transaction_type=operation,
    )
    db.add(journal)
    db.flush()
    debit_account = _account_ledger(db, source) if source else _external_ledger(db, currency)
    credit_account = (
        _account_ledger(db, destination) if destination else _external_ledger(db, currency)
    )
    db.add_all(
        [
            LedgerEntry(
                ledger_transaction_id=journal.id,
                ledger_account_id=debit_account.id,
                debit_or_credit="debit",
                amount=amount,
                currency=currency,
            ),
            LedgerEntry(
                ledger_transaction_id=journal.id,
                ledger_account_id=credit_account.id,
                debit_or_credit="credit",
                amount=amount,
                currency=currency,
            ),
        ]
    )
    if source is not None:
        source.available_balance -= amount
    if destination is not None:
        destination.available_balance += amount
    response = {
        "transaction_id": transaction.id,
        "type": operation,
        "amount": str(amount),
        "currency": currency,
        "status": "posted",
        "replayed": False,
    }
    record.status = "completed"
    record.response_body = json.dumps(response)
    record.response_status = status.HTTP_201_CREATED
    record.financial_transaction_id = transaction.id
    record.completed_at = datetime.now(UTC)
    for affected_account in accounts:
        db.add(
            AuditEvent(
                actor_id=actor.id,
                financial_transaction_id=transaction.id,
                action=operation,
                account_id=affected_account.id,
                attempted_amount=amount,
                result="posted",
                resulting_balance=affected_account.available_balance,
                request_id=get_request_id(),
                idempotency_key=idempotency_key,
            )
        )
    db.commit()
    return response


def post_deposit(
    db: Session, actor: User, account: Account, amount: Decimal, key: str
) -> dict[str, object]:
    return _post(
        db,
        actor,
        "deposit",
        amount,
        account.currency,
        None,
        account,
        key,
        {"account_id": account.id, "amount": str(amount), "currency": account.currency},
    )


def post_withdrawal(
    db: Session, actor: User, account: Account, amount: Decimal, key: str
) -> dict[str, object]:
    return _post(
        db,
        actor,
        "withdrawal",
        amount,
        account.currency,
        account,
        None,
        key,
        {"account_id": account.id, "amount": str(amount), "currency": account.currency},
    )


def post_transfer(
    db: Session,
    actor: User,
    source: Account,
    destination: Account,
    amount: Decimal,
    key: str,
) -> dict[str, object]:
    if source.currency != destination.currency:
        raise HTTPException(status_code=422, detail="Currency mismatch")
    return _post(
        db,
        actor,
        "transfer",
        amount,
        source.currency,
        source,
        destination,
        key,
        {
            "source_account_id": source.id,
            "destination_account_id": destination.id,
            "amount": str(amount),
            "currency": source.currency,
        },
    )
