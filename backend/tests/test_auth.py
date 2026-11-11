from app.core.config import settings
from app.main import app, create_app
from fastapi.testclient import TestClient


def test_login_success(client: TestClient, test_user):
    response = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "correct_password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["login"] == "owner"
    assert settings.COOKIE_NAME in response.cookies


def test_login_invalid_password(client: TestClient, test_user):
    response = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "wrong_password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный логин или пароль"
    assert settings.COOKIE_NAME not in response.cookies


def test_login_invalid_login(client: TestClient, test_user):
    response = client.post(
        "/api/auth/login",
        json={"login": "nonexistent_user", "password": "correct_password"},
    )
    assert response.status_code == 401
    # Одно и то же сообщение об ошибке при неверном логине и неверном пароле
    assert response.json()["detail"] == "Неверный логин или пароль"
    assert settings.COOKIE_NAME not in response.cookies


def test_unauthenticated_request_returns_401(client: TestClient):
    client.cookies.clear()
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "Необходима авторизация" in response.json()["detail"]


def test_authenticated_me_request(client: TestClient, test_user):
    login_res = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "correct_password"},
    )
    assert login_res.status_code == 200

    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["login"] == "owner"


def test_logout(client: TestClient, test_user):
    # Логинимся
    login_res = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "correct_password"},
    )
    assert login_res.status_code == 200

    # Разлогиниваемся
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.json() == {"status": "ok"}

    # Проверяем, что кука удалена и доступ к защищённому эндпоинту закрыт
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 401


def test_login_rate_limiter_blocks_after_5_failed_attempts(client: TestClient, test_user):
    # 5 неудачных попыток должны вернуть 401
    for i in range(5):
        res = client.post(
            "/api/auth/login",
            json={"login": "owner", "password": f"wrong_{i}"},
        )
        assert res.status_code == 401, f"Попытка {i + 1} должна вернуть 401"

    # 6-я попытка с этого же IP должна быть заблокирована с кодом 429
    blocked_res = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "correct_password"},
    )
    assert blocked_res.status_code == 429
    assert "Слишком много попыток входа" in blocked_res.json()["detail"]

    # X-Forwarded-For не должен сбрасывать блокировку (заголовок игнорируется)
    spoofed_res = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "correct_password"},
        headers={"x-forwarded-for": "192.168.1.99"},
    )
    assert spoofed_res.status_code == 429

    # Другой IP (реальный client.host) не должен быть заблокирован
    with TestClient(app, client=("192.168.1.51", 50000)) as other_client:
        other_ip_res = other_client.post(
            "/api/auth/login",
            json={"login": "owner", "password": "correct_password"},
        )
        assert other_ip_res.status_code == 200


def test_login_nonexistent_user_matches_wrong_password_response(client: TestClient, test_user):
    res_wrong_pw = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "wrong_password_123"},
    )
    res_nonexistent = client.post(
        "/api/auth/login",
        json={"login": "completely_nonexistent_user", "password": "wrong_password_123"},
    )
    assert res_wrong_pw.status_code == 401
    assert res_nonexistent.status_code == 401
    assert res_nonexistent.json() == res_wrong_pw.json()


def test_login_nonexistent_user_performs_dummy_hash_verification(client: TestClient, test_user):
    from unittest.mock import patch

    from app.core.security import verify_password
    from app.services.auth import _DUMMY_HASH

    with patch("app.services.auth.verify_password", wraps=verify_password) as mock_verify:
        res = client.post(
            "/api/auth/login",
            json={"login": "nonexistent_user_xyz", "password": "test_password"},
        )
        assert res.status_code == 401
        mock_verify.assert_called_once_with("test_password", _DUMMY_HASH)


def test_production_docs_and_openapi_disabled(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    prod_app = create_app()
    with TestClient(prod_app) as prod_client:
        assert prod_client.get("/docs").status_code == 404
        assert prod_client.get("/redoc").status_code == 404
        assert prod_client.get("/openapi.json").status_code == 404


def test_development_docs_and_openapi_enabled(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    dev_app = create_app()
    with TestClient(dev_app) as dev_client:
        assert dev_client.get("/docs").status_code == 200
        assert dev_client.get("/redoc").status_code == 200
        assert dev_client.get("/openapi.json").status_code == 200
