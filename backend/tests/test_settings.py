from fastapi.testclient import TestClient


def _login_as_owner(client: TestClient, test_user):
    res = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "correct_password"},
    )
    assert res.status_code == 200


def test_settings_require_auth(client: TestClient):
    client.cookies.clear()
    res = client.get("/api/settings")
    assert res.status_code == 401


def test_settings_auto_created_on_first_get(client: TestClient, test_user):
    _login_as_owner(client, test_user)

    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert data["business_name"] == "Студия маникюра"
    assert data["timezone"] == "Europe/Moscow"
    assert data["slot_step_minutes"] == 15


def test_update_settings_success(client: TestClient, test_user):
    _login_as_owner(client, test_user)

    # Обновляем все поля
    update_res = client.put(
        "/api/settings",
        json={
            "business_name": "Эстетика Nails",
            "timezone": "Asia/Yekaterinburg",
            "slot_step_minutes": 30,
        },
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["business_name"] == "Эстетика Nails"
    assert data["timezone"] == "Asia/Yekaterinburg"
    assert data["slot_step_minutes"] == 30

    # Проверяем последующий GET
    get_res = client.get("/api/settings")
    assert get_res.status_code == 200
    assert get_res.json() == data


def test_timezone_validation_invalid_tz(client: TestClient, test_user):
    _login_as_owner(client, test_user)

    res = client.put(
        "/api/settings",
        json={"timezone": "Mars/Base_Alpha"},
    )
    assert res.status_code == 422


def test_slot_step_minutes_validation(client: TestClient, test_user):
    _login_as_owner(client, test_user)

    # Недопустимый шаг (например, 25 или 45)
    invalid_res = client.put(
        "/api/settings",
        json={"slot_step_minutes": 25},
    )
    assert invalid_res.status_code == 422

    # Допустимые шаги: 5, 10, 15, 20, 30, 60
    for valid_step in (5, 10, 15, 20, 30, 60):
        ok_res = client.put(
            "/api/settings",
            json={"slot_step_minutes": valid_step},
        )
        assert ok_res.status_code == 200
        assert ok_res.json()["slot_step_minutes"] == valid_step
