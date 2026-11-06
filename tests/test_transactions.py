from app.schemas import TransactionResponse
from app.transactions import request_hash


def test_request_hash_is_canonical_for_payload_order() -> None:
    first = request_hash("transfer", {"amount": "10.00", "account_id": "a"})
    second = request_hash("transfer", {"account_id": "a", "amount": "10.00"})

    assert first == second


def test_request_hash_changes_for_operation_or_payload() -> None:
    original = request_hash("withdrawal", {"amount": "10.00", "account_id": "a"})

    assert request_hash("deposit", {"amount": "10.00", "account_id": "a"}) != original
    assert request_hash("withdrawal", {"amount": "11.00", "account_id": "a"}) != original


def test_transaction_response_exposes_replay_marker() -> None:
    response = TransactionResponse(
        transaction_id="tx-1",
        type="deposit",
        amount="10.00",
        currency="INR",
        status="posted",
        replayed=True,
    )

    assert response.replayed is True
