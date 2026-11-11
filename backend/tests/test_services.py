from fastapi.testclient import TestClient

from tests.conftest import _login


def test_services_unauthorized(client: TestClient):
    client.cookies.clear()
    res = client.get("/api/services")
    assert res.status_code == 401


def test_create_and_list_services(client: TestClient, test_user):
    _login(client, test_user)

    # Создаём 3 услуги с разным sort_order и активностью
    res1 = client.post(
        "/api/services",
        json={
            "name": "Маникюр классический",
            "price": 1500,
            "duration_minutes": 60,
            "sort_order": 2,
        },
    )
    assert res1.status_code == 201
    s1 = res1.json()

    res2 = client.post(
        "/api/services",
        json={"name": "Снятие покрытия", "price": 500, "duration_minutes": 30, "sort_order": 1},
    )
    assert res2.status_code == 201
    s2 = res2.json()

    res3 = client.post(
        "/api/services",
        json={
            "name": "Архивная услуга",
            "price": 2000,
            "duration_minutes": 90,
            "sort_order": 3,
            "is_active": False,
        },
    )
    assert res3.status_code == 201
    s3 = res3.json()

    # GET по умолчанию — только активные, сортировка по sort_order, затем id
    list_res = client.get("/api/services")
    assert list_res.status_code == 200
    active_services = list_res.json()
    assert len(active_services) == 2
    assert active_services[0]["id"] == s2["id"]  # sort_order = 1
    assert active_services[1]["id"] == s1["id"]  # sort_order = 2

    # GET с include_archived=true — включает архивные
    all_res = client.get("/api/services?include_archived=true")
    assert all_res.status_code == 200
    all_services = all_res.json()
    assert len(all_services) == 3
    assert all_services[2]["id"] == s3["id"]


def test_patch_service(client: TestClient, test_user):
    _login(client, test_user)

    create_res = client.post(
        "/api/services",
        json={"name": "Педикюр", "price": 2500, "duration_minutes": 90},
    )
    assert create_res.status_code == 201
    service_id = create_res.json()["id"]

    # Архивация через PATCH is_active=false и изменение цены
    patch_res = client.patch(
        f"/api/services/{service_id}",
        json={"is_active": False, "price": 2700},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["is_active"] is False
    assert updated["price"] == 2700
    assert updated["name"] == "Педикюр"

    # Проверяем, что в обычном списке её больше нет
    list_res = client.get("/api/services")
    assert service_id not in [s["id"] for s in list_res.json()]


def test_service_validation(client: TestClient, test_user):
    _login(client, test_user)

    # Отрицательная цена
    res = client.post(
        "/api/services",
        json={"name": "Тест", "price": -10, "duration_minutes": 60},
    )
    assert res.status_code == 422

    # Нулевая или отрицательная длительность
    res = client.post(
        "/api/services",
        json={"name": "Тест", "price": 100, "duration_minutes": 0},
    )
    assert res.status_code == 422

    # Пустое имя
    res = client.post(
        "/api/services",
        json={"name": "   ", "price": 100, "duration_minutes": 60},
    )
    assert res.status_code == 422
