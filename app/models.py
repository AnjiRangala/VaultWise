from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(StrEnum):
    ADMINISTRATOR = "administrator"
    ACCOUNT_HOLDER = "account_holder"
    AUDITOR = "auditor"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(String(32), default=UserRole.ACCOUNT_HOLDER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    accounts: Mapped[list["Account"]] = relationship(back_populates="owner")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    account_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[AccountStatus] = mapped_column(String(16), default=AccountStatus.ACTIVE)
    available_balance: Mapped[Decimal] = mapped_column(Numeric(19, 4), default=0)
    overdraft_limit: Mapped[Decimal] = mapped_column(Numeric(19, 4), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped[User] = relationship(back_populates="accounts")


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(16))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3))
    source_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    destination_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default="posted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[str | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True, index=True
    )
    account_code: Mapped[str] = mapped_column(String(64), unique=True)
    account_type: Mapped[str] = mapped_column(String(16))
    currency: Mapped[str] = mapped_column(String(3))


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    financial_transaction_id: Mapped[str] = mapped_column(
        ForeignKey("financial_transactions.id"), unique=True
    )
    transaction_type: Mapped[str] = mapped_column(String(16))
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    ledger_transaction_id: Mapped[str] = mapped_column(
        ForeignKey("ledger_transactions.id"), index=True
    )
    ledger_account_id: Mapped[str] = mapped_column(ForeignKey("ledger_accounts.id"))
    debit_or_credit: Mapped[str] = mapped_column(String(6))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("actor_id", "idempotency_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    idempotency_key: Mapped[str] = mapped_column(String(255))
    request_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="processing")
    response_body: Mapped[str | None] = mapped_column(String, nullable=True)
    response_status: Mapped[int | None] = mapped_column(nullable=True)
    financial_transaction_id: Mapped[str | None] = mapped_column(
        ForeignKey("financial_transactions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    financial_transaction_id: Mapped[str | None] = mapped_column(
        ForeignKey("financial_transactions.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(32))
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    attempted_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 4), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result: Mapped[str] = mapped_column(String(16))
    resulting_balance: Mapped[Decimal | None] = mapped_column(Numeric(19, 4), nullable=True)
    request_id: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
