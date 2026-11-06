from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import AccountStatus, UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountCreateRequest(BaseModel):
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    account_number: str
    currency: str
    status: AccountStatus
    available_balance: Decimal
    created_at: datetime


class MoneyRequest(BaseModel):
    account_id: str
    amount: Decimal = Field(gt=0, decimal_places=4, max_digits=19)


class TransferRequest(BaseModel):
    source_account_id: str
    destination_account_id: str
    amount: Decimal = Field(gt=0, decimal_places=4, max_digits=19)


class TransactionResponse(BaseModel):
    transaction_id: str
    type: str
    amount: str
    currency: str
    status: str
    replayed: bool = False


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    limit: int
    offset: int
    has_more: bool


class StatementEntry(BaseModel):
    transaction_id: str | None
    action: str
    amount: Decimal | None
    result: str
    reason: str | None
    resulting_balance: Decimal | None
    occurred_at: datetime


class ReconciliationResponse(BaseModel):
    account_id: str
    projected_balance: Decimal
    ledger_balance: Decimal
    reconciled: bool
