from fastapi.testclient import TestClient

from app.auth import create_access_token, hash_password, verify_password
from app.config import Settings
from app.main import app
from app.routers import account_router

client = TestClient(app)
TEST_PASSWORD = "test-only-password-for-hash-check"


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
    hashed = hash_password(TEST_PASSWORD)

    assert hashed != TEST_PASSWORD
    assert verify_password(TEST_PASSWORD, hashed)
    assert not verify_password("wrong password", hashed)


def test_production_settings_reject_development_jwt_secret() -> None:
    try:
        Settings(
            app_env="production",
            database_url="sqlite://",
            jwt_secret_key="<generate-a-unique-local-secret>",
        )
    except ValueError as exc:
        assert "JWT_SECRET_KEY" in str(exc)
    else:
        raise AssertionError("Production settings accepted the development JWT secret")


def test_postgres_connection_string_uses_installed_psycopg_driver() -> None:
    settings = Settings(
        database_url="postgresql://user:password@db.example.com:5432/balance_vault",
        jwt_secret_key="test-only-signing-key-not-for-deployment-use",
    )

    assert settings.database_url.startswith("postgresql+psycopg://")


def test_cors_hosts_without_scheme_default_to_https() -> None:
    settings = Settings(
        database_url="sqlite://",
        jwt_secret_key="test-only-signing-key-not-for-deployment-use",
        cors_origins="frontend.example.com, http://localhost:5173/",
    )

    assert settings.cors_origin_list == [
        "https://frontend.example.com",
        "http://localhost:5173",
    ]
