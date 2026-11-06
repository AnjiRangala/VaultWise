from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)
from app.database import get_db
from app.models import (
    Account,
    AccountStatus,
    AuditEvent,
    FinancialTransaction,
    LedgerAccount,
    LedgerEntry,
    User,
    UserRole,
)
from app.schemas import (
    AccountCreateRequest,
    AccountResponse,
    LoginRequest,
    MoneyRequest,
    ReconciliationResponse,
    RegisterRequest,
    StatementEntry,
    TokenResponse,
    TransactionListResponse,
    TransactionResponse,
    TransferRequest,
    UserResponse,
)
from app.transactions import post_deposit, post_transfer, post_withdrawal

auth_router = APIRouter(prefix="/auth", tags=["authentication"])
account_router = APIRouter(prefix="/accounts", tags=["accounts"])
transaction_router = APIRouter(prefix="/transactions", tags=["transactions"])
admin_router = APIRouter(prefix="/admin", tags=["administration"])
audit_router = APIRouter(prefix="/audit", tags=["audit"])


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User).where(User.email == payload.email.lower())) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=UserRole.ACCOUNT_HOLDER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@auth_router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return TokenResponse(access_token=create_access_token(user))


@auth_router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@account_router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreateRequest,
    user: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.ACCOUNT_HOLDER)),
    db: Session = Depends(get_db),
) -> Account:
    account = Account(
        owner_user_id=user.id,
        account_number=f"LL-{uuid4().hex[:20].upper()}",
        currency=payload.currency,
        status=AccountStatus.ACTIVE,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@account_router.get("", response_model=list[AccountResponse])
def list_accounts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Account]:
    return list(
        db.scalars(
            select(Account)
            .where(Account.owner_user_id == user.id)
            .order_by(Account.created_at, Account.id)
        )
    )


@account_router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Account:
    account = db.scalar(
        select(Account).where(Account.id == account_id, Account.owner_user_id == user.id)
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


@account_router.get("/{account_id}/balance", response_model=AccountResponse)
def get_balance(
    account_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Account:
    return _owned_account(db, account_id, user)


@account_router.get("/{account_id}/statement", response_model=list[StatementEntry])
def statement(
    account_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StatementEntry]:
    account = _owned_account(db, account_id, user)
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.account_id == account.id)
        .order_by(AuditEvent.occurred_at, AuditEvent.id)
    )
    return [
        StatementEntry(
            transaction_id=event.financial_transaction_id,
            action=event.action,
            amount=event.attempted_amount,
            result=event.result,
            reason=event.reason,
            resulting_balance=event.resulting_balance,
            occurred_at=event.occurred_at,
        )
        for event in events
    ]


@account_router.get("/{account_id}/reconciliation", response_model=ReconciliationResponse)
def reconciliation(
    account_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReconciliationResponse:
    account = _owned_account(db, account_id, user)
    ledger_balance = db.scalar(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (LedgerEntry.debit_or_credit == "credit", LedgerEntry.amount),
                        else_=-LedgerEntry.amount,
                    )
                ),
                0,
            )
        )
        .join(LedgerAccount, LedgerEntry.ledger_account_id == LedgerAccount.id)
        .where(LedgerAccount.account_id == account.id)
    )
    ledger_balance = Decimal(str(ledger_balance))
    return ReconciliationResponse(
        account_id=account.id,
        projected_balance=account.available_balance,
        ledger_balance=ledger_balance,
        reconciled=account.available_balance == ledger_balance,
    )


def _owned_account(db: Session, account_id: str, user: User) -> Account:
    account = db.scalar(
        select(Account).where(Account.id == account_id, Account.owner_user_id == user.id)
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


@transaction_router.post("/deposit", response_model=TransactionResponse, status_code=201)
def deposit(
    payload: MoneyRequest,
    idempotency_key: str = Header(min_length=8, max_length=255, alias="Idempotency-Key"),
    user: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.ACCOUNT_HOLDER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    account = _owned_account(db, payload.account_id, user)
    return post_deposit(db, user, account, payload.amount, idempotency_key)


@transaction_router.post("/withdraw", response_model=TransactionResponse, status_code=201)
def withdraw(
    payload: MoneyRequest,
    idempotency_key: str = Header(min_length=8, max_length=255, alias="Idempotency-Key"),
    user: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.ACCOUNT_HOLDER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    account = _owned_account(db, payload.account_id, user)
    return post_withdrawal(db, user, account, payload.amount, idempotency_key)


@transaction_router.post("/transfer", response_model=TransactionResponse, status_code=201)
def transfer(
    payload: TransferRequest,
    idempotency_key: str = Header(min_length=8, max_length=255, alias="Idempotency-Key"),
    user: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.ACCOUNT_HOLDER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    source = _owned_account(db, payload.source_account_id, user)
    destination = db.get(Account, payload.destination_account_id)
    if destination is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return post_transfer(db, user, source, destination, payload.amount, idempotency_key)


@transaction_router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    transaction = db.scalar(
        select(FinancialTransaction).where(
            FinancialTransaction.id == transaction_id,
            FinancialTransaction.actor_id == user.id,
        )
    )
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return {
        "transaction_id": transaction.id,
        "type": transaction.transaction_type,
        "amount": str(transaction.amount),
        "currency": transaction.currency,
        "status": transaction.status,
        "replayed": False,
    }


@transaction_router.get("", response_model=TransactionListResponse)
def list_transactions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TransactionListResponse:
    transactions = list(
        db.scalars(
            select(FinancialTransaction)
            .where(FinancialTransaction.actor_id == user.id)
            .order_by(FinancialTransaction.created_at, FinancialTransaction.id)
            .offset(offset)
            .limit(limit + 1)
        )
    )
    has_more = len(transactions) > limit
    items = transactions[:limit]
    return TransactionListResponse(
        items=[
            TransactionResponse(
                transaction_id=item.id,
                type=item.transaction_type,
                amount=str(item.amount),
                currency=item.currency,
                status=item.status,
                replayed=False,
            )
            for item in items
        ],
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@admin_router.get("/users", response_model=list[UserResponse])
def list_users(
    _: User = Depends(require_roles(UserRole.ADMINISTRATOR)),
    db: Session = Depends(get_db),
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at, User.id)))


@admin_router.get("/accounts", response_model=list[AccountResponse])
def list_all_accounts(
    _: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.AUDITOR)),
    db: Session = Depends(get_db),
) -> list[Account]:
    return list(db.scalars(select(Account).order_by(Account.created_at, Account.id)))


@audit_router.get("/events", response_model=list[StatementEntry])
def list_audit_events(
    _: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.AUDITOR)),
    db: Session = Depends(get_db),
) -> list[StatementEntry]:
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.occurred_at, AuditEvent.id))
    return [
        StatementEntry(
            transaction_id=event.financial_transaction_id,
            action=event.action,
            amount=event.attempted_amount,
            result=event.result,
            reason=event.reason,
            resulting_balance=event.resulting_balance,
            occurred_at=event.occurred_at,
        )
        for event in events
    ]
