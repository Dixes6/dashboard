from fastapi.testclient import TestClient

from app.core.config import settings


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
    headers = {"x-forwarded-for": "192.168.1.50"}

    # 5 неудачных попыток должны вернуть 401
    for i in range(5):
        res = client.post(
            "/api/auth/login",
            json={"login": "owner", "password": f"wrong_{i}"},
            headers=headers,
        )
        assert res.status_code == 401, f"Попытка {i + 1} должна вернуть 401"

    # 6-я попытка с этого же IP должна быть заблокирована с кодом 429
    blocked_res = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "correct_password"},
        headers=headers,
    )
    assert blocked_res.status_code == 429
    assert "Слишком много попыток входа" in blocked_res.json()["detail"]

    # Другой IP не должен быть заблокирован
    other_ip_res = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "correct_password"},
        headers={"x-forwarded-for": "192.168.1.51"},
    )
    assert other_ip_res.status_code == 200
