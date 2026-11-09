from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
import psycopg

from tests.conftest import sync_test_url


def _login(client: TestClient, test_user):
    res = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "correct_password"},
    )
    assert res.status_code == 200


def test_clients_unauthorized(client: TestClient):
    client.cookies.clear()
    res = client.get("/api/clients")
    assert res.status_code == 401


def test_create_and_get_client(client: TestClient, test_user):
    _login(client, test_user)

    # Телефон передаётся в произвольном формате, должен нормализоваться
    res = client.post(
        "/api/clients",
        json={
            "name": "Анна Смирнова",
            "phone": "+7 (912) 345-67-89",
            "notes": "Любит нюдовые оттенки",
        },
    )
    assert res.status_code == 201
    created = res.json()
    assert created["name"] == "Анна Смирнова"
    assert created["phone"] == "79123456789"
    assert created["notes"] == "Любит нюдовые оттенки"
    assert created["visits_count"] == 0
    assert created["total_earned"] == 0

    # Получение по ID
    get_res = client.get(f"/api/clients/{created['id']}")
    assert get_res.status_code == 200
    assert get_res.json() == created


def test_patch_and_delete_client(client: TestClient, test_user):
    _login(client, test_user)

    res = client.post(
        "/api/clients",
        json={"name": "Елена", "phone": "89001112233"},
    )
    assert res.status_code == 201
    client_id = res.json()["id"]

    # Обновление
    patch_res = client.patch(
        f"/api/clients/{client_id}",
        json={"name": "Елена Прекрасная", "phone": "+7 900 222-33-44"},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["name"] == "Елена Прекрасная"
    assert updated["phone"] == "79002223344"

    # Мягкое удаление
    del_res = client.delete(f"/api/clients/{client_id}")
    assert del_res.status_code == 200

    # Клиент больше не отдаётся по ID
    get_res = client.get(f"/api/clients/{client_id}")
    assert get_res.status_code == 404

    # Проверяем в БД: строка физически на месте, но deleted_at заполнен
    with psycopg.connect(sync_test_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT deleted_at FROM clients WHERE id = %s", (client_id,))
            row = cur.fetchone()
            assert row is not None
            assert row[0] is not None


def test_client_search_and_pagination(client: TestClient, test_user):
    _login(client, test_user)

    # Создаём несколько клиентов
    client.post("/api/clients", json={"name": "Алина Романова", "phone": "89121111111"})
    client.post("/api/clients", json={"name": "Алиса Воронова", "phone": "89122222222"})
    client.post("/api/clients", json={"name": "Белла Ахматова", "phone": "89203333333"})

    # Поиск по имени q (без учёта регистра)
    res_q = client.get("/api/clients?q=али")
    assert res_q.status_code == 200
    data_q = res_q.json()
    assert data_q["total"] == 2
    assert [c["name"] for c in data_q["items"]] == ["Алина Романова", "Алиса Воронова"]

    # Поиск по началу номера (пользователь вводит 912, 8912 или +7912)
    for query_phone in ["912", "8912", "+7912", "+7 (912)"]:
        res_p = client.get(f"/api/clients?phone={query_phone}")
        assert res_p.status_code == 200
        data_p = res_p.json()
        assert data_p["total"] == 2
        assert len(data_p["items"]) == 2

    # Пагинация
    res_page = client.get("/api/clients?limit=2&offset=1")
    assert res_page.status_code == 200
    data_page = res_page.json()
    assert data_page["total"] == 3
    assert len(data_page["items"]) == 2
    assert data_page["items"][0]["name"] == "Алиса Воронова"


def test_duplicate_phone_conflict(client: TestClient, test_user):
    _login(client, test_user)

    res1 = client.post(
        "/api/clients",
        json={"name": "Клиент 1", "phone": "89120000000"},
    )
    assert res1.status_code == 201

    # Попытка создать клиента с тем же номером
    res2 = client.post(
        "/api/clients",
        json={"name": "Клиент 2", "phone": "+7 (912) 000-00-00"},
    )
    assert res2.status_code == 409
    assert "уже существует" in res2.json()["detail"]

    # Мягко удаляем первого клиента
    client_id1 = res1.json()["id"]
    client.delete(f"/api/clients/{client_id1}")

    # Теперь номер можно зарегистрировать заново (частичный уникальный индекс deleted_at IS NULL)
    res3 = client.post(
        "/api/clients",
        json={"name": "Клиент 3", "phone": "89120000000"},
    )
    assert res3.status_code == 201


def test_client_visits_and_earned_aggregates(client: TestClient, test_user):
    _login(client, test_user)

    res = client.post(
        "/api/clients",
        json={"name": "Виктория", "phone": "89998887766"},
    )
    assert res.status_code == 201
    client_id = res.json()["id"]

    # Добавляем записи напрямую в базу
    now = datetime.now(timezone.utc)
    ends = now + timedelta(hours=1)
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            # 1. Завершена, final_price = 2500 (идёт в доход)
            cur.execute(
                """
                INSERT INTO appointments (client_id, starts_at, ends_at, status, source, list_price, final_price, price_overridden)
                VALUES (%s, %s, %s, 'completed', 'manual', 2500, 2500, false)
                """,
                (client_id, now, ends),
            )
            # 2. Завершена со скидкой, final_price = 3000 (идёт в доход)
            cur.execute(
                """
                INSERT INTO appointments (client_id, starts_at, ends_at, status, source, list_price, final_price, price_overridden)
                VALUES (%s, %s, %s, 'completed', 'manual', 3500, 3000, true)
                """,
                (client_id, now, ends),
            )
            # 3. Запланирована (НЕ должна идти в доход)
            cur.execute(
                """
                INSERT INTO appointments (client_id, starts_at, ends_at, status, source, list_price, final_price, price_overridden)
                VALUES (%s, %s, %s, 'scheduled', 'manual', 2000, 2000, false)
                """,
                (client_id, now, ends),
            )
            # 4. Отменена (НЕ должна идти в доход)
            cur.execute(
                """
                INSERT INTO appointments (client_id, starts_at, ends_at, status, source, list_price, final_price, price_overridden)
                VALUES (%s, %s, %s, 'cancelled', 'manual', 2000, 2000, false)
                """,
                (client_id, now, ends),
            )
            # 5. Мягко удалена completed (НЕ должна идти в доход)
            cur.execute(
                """
                INSERT INTO appointments (client_id, starts_at, ends_at, status, source, list_price, final_price, price_overridden, deleted_at)
                VALUES (%s, %s, %s, 'completed', 'manual', 5000, 5000, false, %s)
                """,
                (client_id, now, ends, now),
            )

    # Проверяем агрегаты в GET /{id} и в общем списке
    client_res = client.get(f"/api/clients/{client_id}")
    assert client_res.status_code == 200
    data = client_res.json()
    assert data["visits_count"] == 2
    assert data["total_earned"] == 5500  # 2500 + 3000

    list_res = client.get("/api/clients")
    assert list_res.status_code == 200
    item = next(c for c in list_res.json()["items"] if c["id"] == client_id)
    assert item["visits_count"] == 2
    assert item["total_earned"] == 5500
