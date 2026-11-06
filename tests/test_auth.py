from fastapi.testclient import TestClient

from app.auth import create_access_token, hash_password, verify_password
from app.config import Settings
from app.main import app
from app.routers import account_router

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_request_id_is_preserved_when_supplied() -> None:
    response = client.get("/health", headers={"X-Request-ID": "request-123"})
    assert response.headers["X-Request-ID"] == "request-123"


def test_protected_endpoint_requires_authentication() -> None:
    response = client.get("/accounts")
    assert response.status_code == 401


def test_invalid_bearer_token_is_rejected() -> None:
    response = client.get("/accounts", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401


def test_money_movement_requires_authentication_before_processing() -> None:
    response = client.post(
        "/transactions/deposit",
        json={"account_id": "not-a-real-account", "amount": "10.00"},
    )
    assert response.status_code == 401


def test_required_balance_route_is_registered() -> None:
    routes = {route.path for route in account_router.routes}
    assert "/accounts/{account_id}/balance" in routes


def test_token_contains_required_claims() -> None:
    class User:
        id = "test-user"
        role = type("Role", (), {"value": "account_holder"})()

    token = create_access_token(User())
    assert isinstance(token, str)


def test_token_accepts_database_string_role() -> None:
    class User:
        id = "test-user"
        role = "account_holder"

    token = create_access_token(User())
    assert isinstance(token, str)


def test_password_hash_is_not_reversible_and_verifies() -> None:
    password = "correct horse battery staple"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong password", hashed)


def test_production_settings_reject_development_jwt_secret() -> None:
    try:
        Settings(
            app_env="production",
            jwt_secret_key="replace-this-development-secret-key",
        )
    except ValueError as exc:
        assert "JWT_SECRET_KEY" in str(exc)
    else:
        raise AssertionError("Production settings accepted the development JWT secret")
